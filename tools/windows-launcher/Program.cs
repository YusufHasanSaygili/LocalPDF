using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;

namespace LocalPDF.Launcher;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new LauncherForm());
    }
}

internal sealed class LauncherForm : Form
{
    private const string LauncherVersion = "0.1.1";
    private const string WebUrl = "http://localhost:3000";
    private const string HealthUrl = "http://localhost:8000/health";

    private readonly string _productRoot = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LocalPDF");
    private readonly string _appRoot;
    private readonly string _dataRoot;
    private readonly RichTextBox _log = new();
    private readonly Label _status = new();
    private readonly Button _start = new();
    private readonly Button _open = new();
    private readonly Button _stop = new();
    private readonly Button _data = new();
    private bool _busy;

    public LauncherForm()
    {
        _appRoot = Path.Combine(_productRoot, "app", LauncherVersion);
        _dataRoot = Path.Combine(_productRoot, "data");

        Text = "LocalPDF";
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(700, 500);
        Size = new Size(780, 560);
        BackColor = Color.FromArgb(245, 245, 239);
        Font = new Font("Segoe UI", 10F);

        BuildInterface();
        Shown += async (_, _) => await InitializeAsync();
    }

    private void BuildInterface()
    {
        var header = new Panel
        {
            Dock = DockStyle.Top,
            Height = 112,
            BackColor = Color.FromArgb(19, 60, 58),
            Padding = new Padding(28, 20, 28, 18)
        };
        var title = new Label
        {
            Text = "LocalPDF",
            ForeColor = Color.White,
            Font = new Font("Georgia", 24F, FontStyle.Bold),
            AutoSize = true,
            Location = new Point(26, 18)
        };
        var subtitle = new Label
        {
            Text = "Private, local-first document processing",
            ForeColor = Color.FromArgb(185, 216, 207),
            AutoSize = true,
            Location = new Point(29, 61)
        };
        _status.Text = "Preparing local application…";
        _status.ForeColor = Color.FromArgb(229, 244, 239);
        _status.AutoSize = true;
        _status.Location = new Point(500, 32);
        header.Controls.Add(title);
        header.Controls.Add(subtitle);
        header.Controls.Add(_status);

        var warning = new Label
        {
            Dock = DockStyle.Top,
            Height = 52,
            Padding = new Padding(28, 16, 18, 8),
            Text = "LocalPDF requires Docker Desktop. Files stay on this computer by default.",
            ForeColor = Color.FromArgb(82, 99, 96)
        };

        var actions = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 66,
            Padding = new Padding(23, 10, 20, 8),
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false
        };
        ConfigureButton(_start, "Start LocalPDF", Color.FromArgb(13, 102, 95), Color.White);
        ConfigureButton(_open, "Open application", Color.FromArgb(227, 241, 237), Color.FromArgb(13, 102, 95));
        ConfigureButton(_stop, "Stop services", Color.White, Color.FromArgb(112, 72, 61));
        ConfigureButton(_data, "Open data folder", Color.White, Color.FromArgb(82, 99, 96));
        _start.Click += async (_, _) => await StartLocalPdfAsync();
        _open.Enabled = false;
        _stop.Enabled = false;
        _open.Click += (_, _) => OpenUrl(WebUrl);
        _stop.Click += async (_, _) => await StopLocalPdfAsync();
        _data.Click += (_, _) => OpenFolder(_dataRoot);
        actions.Controls.AddRange([_start, _open, _stop, _data]);

        _log.Dock = DockStyle.Fill;
        _log.Margin = new Padding(28);
        _log.ReadOnly = true;
        _log.BorderStyle = BorderStyle.None;
        _log.BackColor = Color.White;
        _log.ForeColor = Color.FromArgb(36, 54, 58);
        _log.Font = new Font("Consolas", 9F);
        _log.Padding = new Padding(12);

        var logHost = new Panel { Dock = DockStyle.Fill, Padding = new Padding(28, 6, 28, 26) };
        logHost.Controls.Add(_log);

        Controls.Add(logHost);
        Controls.Add(actions);
        Controls.Add(warning);
        Controls.Add(header);
    }

    private static void ConfigureButton(Button button, string text, Color background, Color foreground)
    {
        button.Text = text;
        button.AutoSize = true;
        button.Height = 40;
        button.Padding = new Padding(12, 4, 12, 4);
        button.Margin = new Padding(5);
        button.FlatStyle = FlatStyle.Flat;
        button.FlatAppearance.BorderColor = Color.FromArgb(210, 220, 215);
        button.BackColor = background;
        button.ForeColor = foreground;
        button.Cursor = Cursors.Hand;
    }

    private async Task InitializeAsync()
    {
        try
        {
            Directory.CreateDirectory(_dataRoot);
            ExtractApplicationBundle();
            AppendLog($"Application files: {_appRoot}");
            AppendLog($"Document data: {_dataRoot}");
            AppendLog("The launcher never uploads document bytes to a vendor service.");

            var docker = FindDockerExecutable();
            if (docker is null)
            {
                SetStatus("Docker Desktop required", Color.FromArgb(255, 218, 138));
                AppendLog("Docker Desktop was not found. Click the button to install it automatically.");
                AppendLog("Windows will ask for administrator approval during installation.");
                _start.Text = "Install Docker & Start";
                return;
            }

            if (await IsStackHealthyAsync())
            {
                SetStatus("Running", Color.FromArgb(108, 218, 176));
                AppendLog("LocalPDF is already running.");
                _open.Enabled = true;
                _stop.Enabled = true;
            }
            else
            {
                SetStatus("Ready to start", Color.FromArgb(229, 244, 239));
            }
        }
        catch (Exception exception)
        {
            SetStatus("Setup failed", Color.FromArgb(255, 190, 180));
            AppendLog(exception.Message);
        }
    }

    private void ExtractApplicationBundle()
    {
        Directory.CreateDirectory(_appRoot);
        var marker = Path.Combine(_appRoot, ".bundle-version");
        if (File.Exists(marker) && File.ReadAllText(marker).Trim() == LauncherVersion &&
            File.Exists(Path.Combine(_appRoot, "docker-compose.yml")))
        {
            return;
        }

        using var resource = Assembly.GetExecutingAssembly()
            .GetManifestResourceStream("LocalPDF.bundle.zip")
            ?? throw new InvalidOperationException("The embedded LocalPDF application bundle is missing.");
        using var archive = new ZipArchive(resource, ZipArchiveMode.Read);
        archive.ExtractToDirectory(_appRoot, overwriteFiles: true);
        File.WriteAllText(marker, LauncherVersion);
    }

    private async Task StartLocalPdfAsync()
    {
        if (_busy)
        {
            return;
        }

        var docker = FindDockerExecutable();
        if (docker is null)
        {
            var answer = MessageBox.Show(
                "LocalPDF needs Docker Desktop. Install the official Docker Desktop package automatically now?\n\nWindows may ask for administrator approval.",
                "Install Docker Desktop",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question);
            if (answer != DialogResult.Yes) return;
        }

        SetBusy(true);
        try
        {
            if (docker is null)
            {
                SetStatus("Installing Docker Desktop...", Color.FromArgb(255, 218, 138));
                docker = await InstallDockerDesktopAsync();
                _start.Text = "Start LocalPDF";
            }

            SetStatus("Starting Docker…", Color.FromArgb(255, 218, 138));
            if (!await IsDockerReadyAsync(docker))
            {
                StartDockerDesktop();
                AppendLog("Waiting for Docker Desktop…");
                var dockerReady = false;
                for (var attempt = 0; attempt < 60; attempt++)
                {
                    await Task.Delay(2000);
                    if (await IsDockerReadyAsync(docker))
                    {
                        dockerReady = true;
                        break;
                    }
                }

                if (!dockerReady)
                {
                    throw new InvalidOperationException(
                        "Docker Desktop did not become ready. Open Docker Desktop and retry.");
                }
            }

            SetStatus("Building services…", Color.FromArgb(255, 218, 138));
            AppendLog("Running: docker compose up -d --build");
            var exitCode = await RunDockerAsync(docker, "compose up -d --build", logOutput: true);
            if (exitCode != 0)
            {
                throw new InvalidOperationException("Docker Compose could not start LocalPDF. See the log above.");
            }

            SetStatus("Waiting for LocalPDF…", Color.FromArgb(255, 218, 138));
            for (var attempt = 0; attempt < 150; attempt++)
            {
                if (await IsStackHealthyAsync())
                {
                    SetStatus("Running", Color.FromArgb(108, 218, 176));
                    AppendLog("LocalPDF is ready at http://localhost:3000");
                    _open.Enabled = true;
                    _stop.Enabled = true;
                    OpenUrl(WebUrl);
                    return;
                }
                await Task.Delay(2000);
            }

            throw new InvalidOperationException("LocalPDF did not become healthy within five minutes.");
        }
        catch (Exception exception)
        {
            SetStatus("Start failed", Color.FromArgb(255, 190, 180));
            AppendLog(exception.Message);
            MessageBox.Show(exception.Message, "LocalPDF", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async Task StopLocalPdfAsync()
    {
        if (_busy)
        {
            return;
        }

        var docker = FindDockerExecutable();
        if (docker is null)
        {
            return;
        }

        SetBusy(true);
        try
        {
            SetStatus("Stopping…", Color.FromArgb(255, 218, 138));
            var exitCode = await RunDockerAsync(docker, "compose down", logOutput: true);
            if (exitCode != 0)
            {
                throw new InvalidOperationException("Docker Compose could not stop LocalPDF.");
            }
            SetStatus("Stopped", Color.FromArgb(229, 244, 239));
            AppendLog("Services stopped. Document data was preserved.");
            _open.Enabled = false;
            _stop.Enabled = false;
        }
        catch (Exception exception)
        {
            AppendLog(exception.Message);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async Task<int> RunDockerAsync(string docker, string arguments, bool logOutput)
    {
        var startInfo = new ProcessStartInfo(docker, arguments)
        {
            WorkingDirectory = _appRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        startInfo.Environment["COMPOSE_PROJECT_NAME"] = "localpdf";
        startInfo.Environment["LOCAL_DATA_DIR"] = _dataRoot.Replace('\\', '/');
        startInfo.Environment["NEXT_PUBLIC_API_BASE_URL"] = "/api/v1";
        startInfo.Environment["API_INTERNAL_URL"] = "http://api:8000";

        using var process = new Process { StartInfo = startInfo };
        if (logOutput)
        {
            process.OutputDataReceived += (_, eventArgs) =>
            {
                if (!string.IsNullOrWhiteSpace(eventArgs.Data)) AppendLog(eventArgs.Data);
            };
            process.ErrorDataReceived += (_, eventArgs) =>
            {
                if (!string.IsNullOrWhiteSpace(eventArgs.Data)) AppendLog(eventArgs.Data);
            };
        }
        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        await process.WaitForExitAsync();
        return process.ExitCode;
    }

    private async Task<string> InstallDockerDesktopAsync()
    {
        var winget = FindExecutableOnPath("winget.exe");
        if (winget is null)
        {
            OpenUrl("https://www.docker.com/products/docker-desktop/");
            throw new InvalidOperationException(
                "Windows Package Manager (winget) was not found. The official Docker download page has been opened; install Docker Desktop, then retry.");
        }

        AppendLog("Installing the official Docker Desktop package with Windows Package Manager...");
        var startInfo = new ProcessStartInfo(
            winget,
            "install --id Docker.DockerDesktop --exact --accept-package-agreements --accept-source-agreements --silent")
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };

        using var process = new Process { StartInfo = startInfo };
        process.OutputDataReceived += (_, eventArgs) =>
        {
            if (!string.IsNullOrWhiteSpace(eventArgs.Data)) AppendLog(eventArgs.Data);
        };
        process.ErrorDataReceived += (_, eventArgs) =>
        {
            if (!string.IsNullOrWhiteSpace(eventArgs.Data)) AppendLog(eventArgs.Data);
        };
        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        await process.WaitForExitAsync();

        var docker = FindDockerExecutable();
        if (process.ExitCode != 0 || docker is null)
        {
            throw new InvalidOperationException(
                $"Docker Desktop installation did not complete (exit code {process.ExitCode}). Retry the installation or use the official Docker installer.");
        }

        AppendLog("Docker Desktop was installed successfully.");
        return docker;
    }

    private async Task<bool> IsDockerReadyAsync(string docker)
    {
        try
        {
            return await RunDockerAsync(docker, "info --format {{.ServerVersion}}", logOutput: false) == 0;
        }
        catch
        {
            return false;
        }
    }

    private static async Task<bool> IsStackHealthyAsync()
    {
        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
            using var response = await client.GetAsync(HealthUrl);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private static string? FindDockerExecutable()
    {
        var fromPath = FindExecutableOnPath("docker.exe");
        if (fromPath is not null) return fromPath;

        var standard = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            "Docker", "Docker", "resources", "bin", "docker.exe");
        return File.Exists(standard) ? standard : null;
    }

    private static string? FindExecutableOnPath(string fileName)
    {
        var pathValue = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        foreach (var path in pathValue.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            var candidate = Path.Combine(path.Trim().Trim('"'), fileName);
            if (File.Exists(candidate)) return candidate;
        }
        return null;
    }

    private static void StartDockerDesktop()
    {
        var executable = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            "Docker", "Docker", "Docker Desktop.exe");
        if (File.Exists(executable))
        {
            Process.Start(new ProcessStartInfo(executable) { UseShellExecute = true });
        }
    }

    private static void OpenUrl(string url) =>
        Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });

    private static void OpenFolder(string path)
    {
        Directory.CreateDirectory(path);
        Process.Start(new ProcessStartInfo("explorer.exe", path) { UseShellExecute = true });
    }

    private void SetBusy(bool busy)
    {
        _busy = busy;
        _start.Enabled = !busy;
        _data.Enabled = !busy;
        if (busy)
        {
            _open.Enabled = false;
            _stop.Enabled = false;
        }
    }

    private void SetStatus(string text, Color color)
    {
        if (InvokeRequired)
        {
            BeginInvoke(() => SetStatus(text, color));
            return;
        }
        _status.Text = text;
        _status.ForeColor = color;
    }

    private void AppendLog(string message)
    {
        if (InvokeRequired)
        {
            BeginInvoke(() => AppendLog(message));
            return;
        }
        _log.AppendText($"[{DateTime.Now:HH:mm:ss}] {message}{Environment.NewLine}");
        _log.SelectionStart = _log.TextLength;
        _log.ScrollToCaret();
    }
}
