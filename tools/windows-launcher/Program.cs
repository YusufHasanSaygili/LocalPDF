using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace LocalPDF.Desktop;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new DesktopForm());
    }
}

internal sealed class DesktopForm : Form
{
    private const string AppVersion = "0.2.0";
    private const string WebUrl = "http://127.0.0.1:3000";
    private const string ApiHealthUrl = "http://127.0.0.1:8000/ready";

    private readonly string _productRoot = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LocalPDF");
    private readonly string _appRoot;
    private readonly string _dataRoot;
    private readonly Panel _startupPanel = new();
    private readonly Label _status = new();
    private readonly RichTextBox _log = new();
    private readonly WebView2 _webView = new();
    private Process? _apiProcess;
    private Process? _webProcess;

    public DesktopForm()
    {
        _appRoot = Path.Combine(_productRoot, "app", AppVersion);
        _dataRoot = Path.Combine(_productRoot, "data");

        Text = "LocalPDF";
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(960, 680);
        Size = new Size(1380, 900);
        BackColor = Color.FromArgb(245, 245, 239);
        Font = new Font("Segoe UI", 10F);

        BuildInterface();
        Shown += async (_, _) => await StartApplicationAsync();
        FormClosing += (_, _) => StopChildProcesses();
    }

    private void BuildInterface()
    {
        _webView.Dock = DockStyle.Fill;
        _webView.Visible = false;

        _startupPanel.Dock = DockStyle.Fill;
        _startupPanel.BackColor = Color.FromArgb(245, 245, 239);

        var card = new Panel
        {
            Size = new Size(720, 430),
            BackColor = Color.White,
            Anchor = AnchorStyles.None,
            Location = new Point((ClientSize.Width - 720) / 2, (ClientSize.Height - 430) / 2)
        };
        _startupPanel.Resize += (_, _) => card.Location = new Point(
            Math.Max(0, (_startupPanel.ClientSize.Width - card.Width) / 2),
            Math.Max(0, (_startupPanel.ClientSize.Height - card.Height) / 2));

        var title = new Label
        {
            Text = "LocalPDF",
            Font = new Font("Georgia", 28F, FontStyle.Bold),
            ForeColor = Color.FromArgb(19, 60, 58),
            AutoSize = true,
            Location = new Point(32, 24)
        };
        var subtitle = new Label
        {
            Text = "Private, local-first document processing",
            ForeColor = Color.FromArgb(82, 99, 96),
            AutoSize = true,
            Location = new Point(35, 78)
        };
        _status.Text = "Starting local application...";
        _status.Font = new Font("Segoe UI Semibold", 11F);
        _status.ForeColor = Color.FromArgb(13, 102, 95);
        _status.AutoSize = true;
        _status.Location = new Point(35, 122);

        _log.ReadOnly = true;
        _log.BorderStyle = BorderStyle.None;
        _log.BackColor = Color.FromArgb(248, 250, 248);
        _log.ForeColor = Color.FromArgb(36, 54, 58);
        _log.Font = new Font("Consolas", 9F);
        _log.Location = new Point(35, 164);
        _log.Size = new Size(650, 220);

        var privacy = new Label
        {
            Text = "No Docker. No cloud upload. Your files stay on this computer.",
            ForeColor = Color.FromArgb(82, 99, 96),
            AutoSize = true,
            Location = new Point(35, 398)
        };

        card.Controls.AddRange([title, subtitle, _status, _log, privacy]);
        _startupPanel.Controls.Add(card);
        Controls.Add(_webView);
        Controls.Add(_startupPanel);
    }

    private async Task StartApplicationAsync()
    {
        try
        {
            Directory.CreateDirectory(_dataRoot);
            SetStatus("Preparing desktop runtime...");
            await Task.Run(ExtractRuntime);
            AppendLog($"Application runtime: {_appRoot}");
            AppendLog($"Private data: {_dataRoot}");

            if (await IsHealthyAsync(ApiHealthUrl) || await IsHealthyAsync(WebUrl))
            {
                throw new InvalidOperationException(
                    "LocalPDF ports are already in use. Close any older LocalPDF instance and retry.");
            }

            SetStatus("Starting local document engine...");
            _apiProcess = StartApi();
            if (!await WaitForHealthAsync(ApiHealthUrl, TimeSpan.FromSeconds(45)))
            {
                throw new InvalidOperationException("The local document engine could not start.");
            }

            SetStatus("Starting desktop interface...");
            _webProcess = StartWeb();
            if (!await WaitForHealthAsync(WebUrl, TimeSpan.FromSeconds(45)))
            {
                throw new InvalidOperationException("The desktop interface could not start.");
            }

            SetStatus("Opening LocalPDF...");
            var webViewData = Path.Combine(_dataRoot, "webview");
            var environment = await CoreWebView2Environment.CreateAsync(null, webViewData);
            await _webView.EnsureCoreWebView2Async(environment);
            _webView.CoreWebView2.Settings.AreDevToolsEnabled = false;
            _webView.CoreWebView2.Settings.IsStatusBarEnabled = false;
            _webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = true;
            _webView.Source = new Uri(WebUrl);
            _webView.Visible = true;
            _startupPanel.Visible = false;
        }
        catch (Exception exception)
        {
            SetStatus("LocalPDF could not start", Color.FromArgb(174, 58, 45));
            AppendLog(exception.Message);
            MessageBox.Show(exception.Message, "LocalPDF", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void ExtractRuntime()
    {
        var marker = Path.Combine(_appRoot, ".runtime-version");
        if (File.Exists(marker) && File.ReadAllText(marker).Trim() == AppVersion &&
            File.Exists(Path.Combine(_appRoot, "api", "LocalPDF.Api.exe")) &&
            File.Exists(Path.Combine(_appRoot, "web", "server.js")) &&
            File.Exists(Path.Combine(_appRoot, "runtime", "node.exe")))
        {
            return;
        }

        Directory.CreateDirectory(_appRoot);
        using var resource = Assembly.GetExecutingAssembly()
            .GetManifestResourceStream("LocalPDF.bundle.zip")
            ?? throw new InvalidOperationException("The embedded desktop runtime is missing.");
        using var archive = new ZipArchive(resource, ZipArchiveMode.Read);
        archive.ExtractToDirectory(_appRoot, overwriteFiles: true);
        File.WriteAllText(marker, AppVersion);
    }

    private Process StartApi()
    {
        var executable = Path.Combine(_appRoot, "api", "LocalPDF.Api.exe");
        var database = Path.Combine(_dataRoot, "localpdf.sqlite3").Replace('\\', '/');
        var startInfo = HiddenProcess(executable, _appRoot);
        startInfo.Environment["DATABASE_URL"] = $"sqlite+pysqlite:///{database}";
        startInfo.Environment["LOCAL_DATA_DIR"] = _dataRoot;
        startInfo.Environment["LOCALPDF_API_PORT"] = "8000";
        startInfo.Environment["TELEMETRY_ENABLED"] = "false";
        return StartLoggedProcess(startInfo, "engine");
    }

    private Process StartWeb()
    {
        var node = Path.Combine(_appRoot, "runtime", "node.exe");
        var webRoot = Path.Combine(_appRoot, "web");
        var startInfo = HiddenProcess(node, webRoot, "server.js");
        startInfo.Environment["HOSTNAME"] = "127.0.0.1";
        startInfo.Environment["PORT"] = "3000";
        startInfo.Environment["API_INTERNAL_URL"] = "http://127.0.0.1:8000";
        startInfo.Environment["NEXT_PUBLIC_API_BASE_URL"] = "/api/v1";
        startInfo.Environment["NEXT_TELEMETRY_DISABLED"] = "1";
        return StartLoggedProcess(startInfo, "interface");
    }

    private static ProcessStartInfo HiddenProcess(string executable, string workingDirectory, string? argument = null)
    {
        var startInfo = new ProcessStartInfo(executable)
        {
            WorkingDirectory = workingDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        if (argument is not null) startInfo.ArgumentList.Add(argument);
        return startInfo;
    }

    private Process StartLoggedProcess(ProcessStartInfo startInfo, string name)
    {
        var process = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
        process.OutputDataReceived += (_, args) =>
        {
            if (!string.IsNullOrWhiteSpace(args.Data)) AppendLog($"[{name}] {args.Data}");
        };
        process.ErrorDataReceived += (_, args) =>
        {
            if (!string.IsNullOrWhiteSpace(args.Data)) AppendLog($"[{name}] {args.Data}");
        };
        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        return process;
    }

    private static async Task<bool> WaitForHealthAsync(string url, TimeSpan timeout)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            if (await IsHealthyAsync(url)) return true;
            await Task.Delay(350);
        }
        return false;
    }

    private static async Task<bool> IsHealthyAsync(string url)
    {
        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
            using var response = await client.GetAsync(url);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private void StopChildProcesses()
    {
        StopProcess(_webProcess);
        StopProcess(_apiProcess);
    }

    private static void StopProcess(Process? process)
    {
        try
        {
            if (process is { HasExited: false }) process.Kill(entireProcessTree: true);
        }
        catch
        {
            // Windows is already tearing down the process tree.
        }
    }

    private void SetStatus(string text, Color? color = null)
    {
        if (InvokeRequired)
        {
            BeginInvoke(() => SetStatus(text, color));
            return;
        }
        _status.Text = text;
        if (color.HasValue) _status.ForeColor = color.Value;
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
