using System.Runtime.InteropServices;
using System.Windows;

namespace ChzzkNotifier;

public partial class App : Application
{
    public const string AppTitle = "치지직 방송 알리미";

    private Mutex? _mutex;

    [DllImport("user32.dll")] private static extern nint FindWindowW(string? cls, string title);
    [DllImport("user32.dll")] private static extern bool ShowWindow(nint hwnd, int cmd);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(nint hwnd);

    protected override void OnStartup(StartupEventArgs e)
    {
        _mutex = new Mutex(true, "ChzzkLiveNotifier_SingleInstance", out var createdNew);
        if (!createdNew)
        {
            // 이미 실행 중 → 기존 창을 앞으로 가져오고 종료
            var hwnd = FindWindowW(null, AppTitle);
            if (hwnd != 0)
            {
                ShowWindow(hwnd, 9); // SW_RESTORE
                SetForegroundWindow(hwnd);
            }
            Shutdown();
            return;
        }

        base.OnStartup(e);

        // 디스코드 블러플 액센트 (Primary 버튼/토글 색상)
        Wpf.Ui.Appearance.ApplicationAccentColorManager.Apply(
            System.Windows.Media.Color.FromRgb(0x58, 0x65, 0xF2),
            Wpf.Ui.Appearance.ApplicationTheme.Dark);

        var minimized = e.Args.Contains("--minimized");
        var window = new MainWindow();
        MainWindow = window;
        if (!minimized)
            window.Show();
    }
}
