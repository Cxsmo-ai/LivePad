using System.Diagnostics;
using System.IO.Pipes;
using System.Text.Json;
using HIDMaestro;

const string pipeName = "TikForeverGamepad";
const string profileId = "xbox-360-wired";
var mockMode = args.Contains("--mock", StringComparer.OrdinalIgnoreCase);

HMContext? context = null;
HMController? controller = null;
HMProfile? profile = null;
long mockFrames = 0;
long mockNeutralizations = 0;
var submissionLock = new object();
Action<JsonElement> submitState;
Action submitNeutral;

if (mockMode)
{
    submitState = _ => Interlocked.Increment(ref mockFrames);
    submitNeutral = () => Interlocked.Increment(ref mockNeutralizations);
    Console.WriteLine($"Mock bridge serving {profileId}");
}
else
{
    context = new HMContext();
    var loadedProfiles = context.LoadDefaultProfiles();
    profile = context.GetProfile(profileId)
        ?? throw new InvalidOperationException($"HIDMaestro profile '{profileId}' was not found");
    controller = context.CreateController(profile);
    submitState = root =>
    {
        lock (submissionLock)
            SubmitState(controller, profile, root);
    };
    submitNeutral = () =>
    {
        lock (submissionLock)
            SubmitNeutral(controller, profile);
    };
    submitNeutral();
    Console.WriteLine($"Loaded {loadedProfiles} profiles; serving {profileId}");
    Console.WriteLine("Driver installation is intentionally not automatic.");
}

using var pipe = new NamedPipeServerStream(
    pipeName,
    PipeDirection.InOut,
    1,
    PipeTransmissionMode.Byte,
    PipeOptions.Asynchronous);

await pipe.WaitForConnectionAsync();
using var reader = new StreamReader(pipe, leaveOpen: true);
using var writer = new StreamWriter(pipe, leaveOpen: true) { AutoFlush = true };
long lastHeartbeat = Stopwatch.GetTimestamp();
using var watchdogCts = new CancellationTokenSource();
var watchdog = WatchdogLoop(submitNeutral, () => Volatile.Read(ref lastHeartbeat), watchdogCts.Token);

await writer.WriteLineAsync(JsonSerializer.Serialize(new { type = "ready", profile = profileId, mock = mockMode }));

var shutdownRequested = false;
while (true)
{
    var line = await reader.ReadLineAsync();
    if (line is null)
        break;

    try
    {
        using var document = JsonDocument.Parse(line);
        var root = document.RootElement;
        var type = root.GetProperty("type").GetString();
        Volatile.Write(ref lastHeartbeat, Stopwatch.GetTimestamp());

        switch (type)
        {
            case "state":
                submitState(root);
                break;
            case "heartbeat":
                break;
            case "clear":
                submitNeutral();
                break;
            case "shutdown":
                submitNeutral();
                shutdownRequested = true;
                break;
            default:
                await writer.WriteLineAsync(JsonSerializer.Serialize(
                    new { type = "error", message = $"unsupported message type: {type}" }));
                break;
        }
        if (shutdownRequested)
            break;
    }
    catch (Exception error) when (error is JsonException or KeyNotFoundException
                                  or FormatException or InvalidOperationException
                                  or OverflowException)
    {
        await writer.WriteLineAsync(JsonSerializer.Serialize(new { type = "error", message = error.Message }));
    }
}

watchdogCts.Cancel();
await watchdog;
submitNeutral();
controller?.Dispose();
context?.Dispose();
Console.WriteLine(mockMode
    ? $"Mock frames received: {mockFrames}; neutralizations: {mockNeutralizations}"
    : "Controller neutralized and disposed");

static async Task WatchdogLoop(Action submitNeutral, Func<long> lastHeartbeat, CancellationToken cancellationToken)
{
    var neutralized = false;
    while (!cancellationToken.IsCancellationRequested)
    {
        try
        {
            await Task.Delay(250, cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            break;
        }
        var elapsed = Stopwatch.GetElapsedTime(lastHeartbeat());
        if (elapsed >= TimeSpan.FromSeconds(1) && !neutralized)
        {
            submitNeutral();
            neutralized = true;
        }
        else if (elapsed < TimeSpan.FromSeconds(1))
        {
            neutralized = false;
        }
    }
}

static void SubmitState(HMController controller, HMProfile profile, JsonElement root)
{
    var lt = ToTrigger(root, "lt");
    var rt = ToTrigger(root, "rt");
    var axes = HMGamepadStateHelpers.StandardAxes(
        profile,
        ToAxis(root, "lx"),
        ToAxis(root, "ly"),
        ToAxis(root, "rx"),
        ToAxis(root, "ry"),
        lt,
        rt);

    if (profile.AvailableAxes.Contains(HMAxis.Z))
    {
        axes[HMAxis.Z] = Math.Clamp((rt - lt + 1f) / 2f, 0f, 1f);
    }

    var state = new HMGamepadState
    {
        Axes = axes,
        Buttons = ParseButtons(root),
    };
    controller.SubmitState(in state);
}

static void SubmitNeutral(HMController controller, HMProfile profile)
{
    var axes = HMGamepadStateHelpers.StandardAxes(
        profile,
        leftStickX: 0.5f,
        leftStickY: 0.5f,
        rightStickX: 0.5f,
        rightStickY: 0.5f,
        leftTrigger: 0f,
        rightTrigger: 0f);

    if (profile.AvailableAxes.Contains(HMAxis.Z))
    {
        axes[HMAxis.Z] = 0.5f;
    }

    var state = new HMGamepadState
    {
        Axes = axes,
        Buttons = HMButton.None,
    };
    controller.SubmitState(in state);
}

static float ToAxis(JsonElement root, string name)
{
    var value = root.TryGetProperty(name, out var property) ? property.GetSingle() : 0f;
    return Math.Clamp((value + 1f) / 2f, 0f, 1f);
}

static float ToTrigger(JsonElement root, string name)
{
    var value = root.TryGetProperty(name, out var property) ? property.GetSingle() : 0f;
    return Math.Clamp(value, 0f, 1f);
}

static HMButton ParseButtons(JsonElement root)
{
    if (!root.TryGetProperty("buttons", out var buttons) || buttons.ValueKind != JsonValueKind.Array)
        return HMButton.None;

    var result = HMButton.None;
    foreach (var value in buttons.EnumerateArray())
    {
        result |= value.GetString()?.ToLowerInvariant() switch
        {
            "a" => HMButton.A,
            "b" => HMButton.B,
            "x" => HMButton.X,
            "y" => HMButton.Y,
            "lb" => HMButton.LeftBumper,
            "rb" => HMButton.RightBumper,
            "l3" => HMButton.LeftStick,
            "r3" => HMButton.RightStick,
            "start" => HMButton.Start,
            "back" => HMButton.Back,
            _ => HMButton.None,
        };
    }
    return result;
}
