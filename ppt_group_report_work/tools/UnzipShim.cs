using System;
using System.Diagnostics;
using System.Linq;

public static class UnzipShim
{
    public static int Main(string[] args)
    {
        string[] tarArgs;
        if (args.Length == 2 && args[0] == "-Z1")
        {
            tarArgs = new[] { "-tf", args[1] };
        }
        else if (args.Length == 3 && args[0] == "-p")
        {
            tarArgs = new[] { "-xOf", args[1], args[2] };
        }
        else
        {
            Console.Error.WriteLine("Unsupported unzip arguments");
            return 2;
        }

        var start = new ProcessStartInfo
        {
            FileName = "tar.exe",
            UseShellExecute = false,
        };
        start.Arguments = string.Join(" ", tarArgs.Select(Quote));
        using (var process = Process.Start(start))
        {
            process.WaitForExit();
            return process.ExitCode;
        }
    }

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }
}
