using System.ComponentModel;
using System.IO;
using System.Windows;

namespace ChzzkNotifier;

public partial class MainWindow
{
    private readonly NotifierCore _core = NotifierCore.Instance;
    private System.Windows.Forms.NotifyIcon? _tray;
    private bool _exiting;

    private readonly StreamersPage _streamersPage = new();
    private SettingsPage? _settingsPage;

    public MainWindow()
    {
        InitializeComponent();
        DataContext = _core;
        SetupTray();
        Closing += OnClosingToTray;
        SelectPage("home");
        _core.Start();
    }

    private void SelectPage(string page)
    {
        HomeBtn.Tag = page == "home" ? "selected" : null;
        SettingsBtn.Tag = page == "settings" ? "selected" : null;
        if (page == "home")
            ContentFrame.Navigate(_streamersPage);
        else
            ContentFrame.Navigate(_settingsPage ??= new SettingsPage());
    }

    private void HomeBtn_Click(object sender, RoutedEventArgs e) => SelectPage("home");
    private void SettingsBtn_Click(object sender, RoutedEventArgs e) => SelectPage("settings");

    private void AddBtn_Click(object sender, RoutedEventArgs e) =>
        new AddStreamerWindow { Owner = this }.ShowDialog();

    // ---------------- 트레이 ----------------

    private void SetupTray()
    {
        var iconPath = Path.Combine(AppConfig.BaseDir, "logo.ico");
        var trayIcon = File.Exists(iconPath)
            ? new System.Drawing.Icon(iconPath)
            : (Environment.ProcessPath is { } exe
                ? System.Drawing.Icon.ExtractAssociatedIcon(exe) : null)
              ?? System.Drawing.SystemIcons.Application;
        _tray = new System.Windows.Forms.NotifyIcon
        {
            Icon = trayIcon,
            Text = App.AppTitle,
            Visible = true,
        };
        _tray.DoubleClick += (_, _) => ShowFromTray();
        var menu = new System.Windows.Forms.ContextMenuStrip();
        menu.Items.Add("열기", null, (_, _) => ShowFromTray());
        menu.Items.Add("지금 새로고침", null, (_, _) => _core.RefreshNow());
        menu.Items.Add("종료", null, (_, _) => ExitApp());
        _tray.ContextMenuStrip = menu;
    }

    private void ShowFromTray()
    {
        Dispatcher.Invoke(() =>
        {
            Show();
            WindowState = WindowState.Normal;
            Activate();
        });
    }

    private void OnClosingToTray(object? sender, CancelEventArgs e)
    {
        if (_exiting) return;
        e.Cancel = true;   // 종료 대신 트레이로
        Hide();
    }

    private void ExitApp()
    {
        _exiting = true;
        _core.Exiting = true;
        _tray?.Dispose();
        Application.Current.Shutdown();
    }

    protected override void OnClosed(EventArgs e)
    {
        _tray?.Dispose();
        base.OnClosed(e);
    }
}
