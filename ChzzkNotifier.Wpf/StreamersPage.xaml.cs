using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace ChzzkNotifier;

public partial class StreamersPage : Page
{
    private readonly NotifierCore _core = NotifierCore.Instance;

    public StreamersPage()
    {
        InitializeComponent();
        FollowList.ItemsSource = _core.FollowItems;
    }

    private void FollowList_MouseDoubleClick(object sender, MouseButtonEventArgs e) => OpenSelected();
    private void OpenButton_Click(object sender, RoutedEventArgs e) => OpenSelected();

    private void OpenSelected()
    {
        if (FollowList.SelectedItem is not FollowItem item) return;
        Process.Start(new ProcessStartInfo(ChzzkApi.LiveUrl(item.Channel.ChannelId))
        { UseShellExecute = true });
    }

    private void RemoveButton_Click(object sender, RoutedEventArgs e)
    {
        if (FollowList.SelectedItem is not FollowItem item) return;
        _core.Config.Channels.RemoveAll(c => c.ChannelId == item.Channel.ChannelId);
        _core.Config.Save();
        _core.FollowItems.Remove(item);
        _core.Status = $"{item.Name} 제거됨";
    }

    private void RefreshButton_Click(object sender, RoutedEventArgs e) => _core.RefreshNow();

    private void TestButton_Click(object sender, RoutedEventArgs e) =>
        _core.TestNotification((FollowList.SelectedItem as FollowItem)?.Channel);
}
