using System;
using System.Diagnostics;
using System.Linq;

public static class Python3Shim
{
    public static int Main(string[] args)
    {
        var start = new ProcessStartInfo
        {
            FileName = @"C:\Users\brett\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
            UseShellExecute = false,
            Arguments = string.Join(" ", args.Select(Quote)),
        };
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
