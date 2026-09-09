using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Windows.Forms;

internal static class StandaloneInstaller
{
    private const string AppName = "Baixatudo";
    private const string PayloadResourceName = "BaixatudoPayload.zip";

    [STAThread]
    private static int Main()
    {
        try
        {
            string installDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs",
                AppName
            );
            string toolsDir = Path.Combine(installDir, "tools");
            string launcherCmd = Path.Combine(installDir, "Iniciar Baixatudo.cmd");
            string launcherVbs = Path.Combine(installDir, "Abrir Baixatudo.vbs");

            Directory.CreateDirectory(installDir);
            Directory.CreateDirectory(toolsDir);
            ExtractPayload(installDir);
            WriteHiddenLauncher(launcherVbs);
            CreateShortcuts(launcherVbs, installDir);

            if (PythonAvailable())
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "wscript.exe"),
                    Arguments = Quote(launcherVbs),
                    WorkingDirectory = installDir,
                    UseShellExecute = true
                });

                MessageBox.Show(
                    AppName + " foi instalado.\r\n\r\nAtalho criado na Area de Trabalho e no menu Iniciar.",
                    AppName,
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            }
            else
            {
                MessageBox.Show(
                    AppName + " foi instalado, mas este computador precisa do Python 3 para abrir o app.\r\n\r\nInstale o Python para Windows e use o atalho Baixatudo.",
                    AppName,
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
            }

            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Nao foi possivel instalar o " + AppName + ".\r\n\r\n" + ex.Message,
                AppName,
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
            return 1;
        }
    }

    private static void ExtractPayload(string installDir)
    {
        Assembly assembly = Assembly.GetExecutingAssembly();
        using (Stream stream = assembly.GetManifestResourceStream(PayloadResourceName))
        {
            if (stream == null)
            {
                throw new InvalidOperationException("Pacote interno nao encontrado.");
            }

            using (ZipArchive archive = new ZipArchive(stream, ZipArchiveMode.Read))
            {
                string installRoot = Path.GetFullPath(installDir);
                foreach (ZipArchiveEntry entry in archive.Entries)
                {
                    string destination = Path.GetFullPath(Path.Combine(installDir, entry.FullName));
                    if (!destination.StartsWith(installRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) &&
                        !string.Equals(destination, installRoot, StringComparison.OrdinalIgnoreCase))
                    {
                        throw new InvalidOperationException("Arquivo invalido no pacote interno.");
                    }

                    if (entry.FullName.EndsWith("/", StringComparison.Ordinal) ||
                        entry.FullName.EndsWith("\\", StringComparison.Ordinal))
                    {
                        Directory.CreateDirectory(destination);
                        continue;
                    }

                    string directory = Path.GetDirectoryName(destination);
                    if (!string.IsNullOrEmpty(directory))
                    {
                        Directory.CreateDirectory(directory);
                    }

                    entry.ExtractToFile(destination, true);
                }
            }
        }
    }

    private static void WriteHiddenLauncher(string launcherVbs)
    {
        string script =
            "Set shell = CreateObject(\"WScript.Shell\")\r\n" +
            "Set fso = CreateObject(\"Scripting.FileSystemObject\")\r\n" +
            "appDir = fso.GetParentFolderName(WScript.ScriptFullName)\r\n" +
            "shell.Run \"\"\"\" & appDir & \"\\Iniciar Baixatudo.cmd\" & \"\"\"\", 0, False\r\n";

        File.WriteAllText(launcherVbs, script);
    }

    private static void CreateShortcuts(string launcherVbs, string installDir)
    {
        string wscript = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "wscript.exe");
        string icon = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "shell32.dll") + ",220";
        string startMenu = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), AppName + ".lnk");
        string desktop = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), AppName + ".lnk");

        CreateShortcut(startMenu, wscript, Quote(launcherVbs), installDir, icon);
        CreateShortcut(desktop, wscript, Quote(launcherVbs), installDir, icon);
    }

    private static void CreateShortcut(string shortcutPath, string targetPath, string arguments, string workingDirectory, string iconLocation)
    {
        Type shellType = Type.GetTypeFromProgID("WScript.Shell");
        if (shellType == null)
        {
            throw new InvalidOperationException("WScript.Shell nao esta disponivel.");
        }

        object shell = Activator.CreateInstance(shellType);
        object shortcut = shellType.InvokeMember(
            "CreateShortcut",
            BindingFlags.InvokeMethod,
            null,
            shell,
            new object[] { shortcutPath }
        );
        Type shortcutType = shortcut.GetType();

        shortcutType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, shortcut, new object[] { targetPath });
        shortcutType.InvokeMember("Arguments", BindingFlags.SetProperty, null, shortcut, new object[] { arguments });
        shortcutType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, shortcut, new object[] { workingDirectory });
        shortcutType.InvokeMember("IconLocation", BindingFlags.SetProperty, null, shortcut, new object[] { iconLocation });
        shortcutType.InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, null);
    }

    private static bool PythonAvailable()
    {
        string[] commands = { "pyw.exe", "pythonw.exe", "py.exe", "python.exe" };
        foreach (string command in commands)
        {
            if (!string.IsNullOrEmpty(FindOnPath(command)))
            {
                return true;
            }
        }

        string localPython = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Programs",
            "Python"
        );
        if (ContainsFile(localPython, "pythonw.exe"))
        {
            return true;
        }

        if (ContainsFile(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "pythonw.exe"))
        {
            return true;
        }

        string programFilesX86 = Environment.GetEnvironmentVariable("ProgramFiles(x86)");
        return !string.IsNullOrEmpty(programFilesX86) && ContainsFile(programFilesX86, "pythonw.exe");
    }

    private static bool ContainsFile(string root, string fileName)
    {
        try
        {
            if (string.IsNullOrEmpty(root) || !Directory.Exists(root))
            {
                return false;
            }

            string[] files = Directory.GetFiles(root, fileName, SearchOption.AllDirectories);
            return files.Length > 0;
        }
        catch
        {
            return false;
        }
    }

    private static string FindOnPath(string fileName)
    {
        string path = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        foreach (string part in path.Split(Path.PathSeparator))
        {
            try
            {
                if (string.IsNullOrWhiteSpace(part))
                {
                    continue;
                }

                string candidate = Path.Combine(part.Trim('"'), fileName);
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
            catch
            {
            }
        }

        return null;
    }

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }
}
