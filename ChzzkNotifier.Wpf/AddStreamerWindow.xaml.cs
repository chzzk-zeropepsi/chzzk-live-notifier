using System.Windows;
using System.Windows.Input;

namespace ChzzkNotifier;

public partial class AddStreamerWindow
{
    private readonly NotifierCore _core = NotifierCore.Instance;

    public AddStreamerWindow()
    {
        InitializeComponent();
        SearchList.ItemsSource = _core.SearchItems;
        Loaded += (_, _) => SearchBox.Focus();
    }

    private void SearchBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) _ = DoSearchAsync();
    }

    private void SearchButton_Click(object sender, RoutedEventArgs e) => _ = DoSearchAsync();

    private async Task DoSearchAsync()
    {
        var keyword = SearchBox.Text.Trim();
        if (keyword.Length == 0) return;
        HintText.Text = $"'{keyword}' 검색 중…";
        try
        {
            var results = await ChzzkApi.SearchChannelsAsync(keyword);
            _core.SearchItems.Clear();
            foreach (var r in results)
                _core.SearchItems.Add(new SearchItem(r));
            HintText.Text = $"검색 결과 {results.Count}개 — 더블클릭으로 바로 추가";
        }
        catch (Exception ex)
        {
            HintText.Text = $"검색 실패: {ex.Message}";
        }
    }

    private void SearchList_MouseDoubleClick(object sender, MouseButtonEventArgs e) => AddSelected();
    private void AddButton_Click(object sender, RoutedEventArgs e) => AddSelected();

    private void AddSelected()
    {
        if (SearchList.SelectedItem is not SearchItem item)
        {
            HintText.Text = "추가할 채널을 목록에서 선택하세요.";
            return;
        }
        if (_core.Config.Channels.Any(c => c.ChannelId == item.Result.ChannelId))
        {
            HintText.Text = $"{item.Result.ChannelName} 은(는) 이미 목록에 있습니다.";
            return;
        }
        var ch = new FollowedChannel
        {
            ChannelId = item.Result.ChannelId,
            ChannelName = item.Result.ChannelName,
            ChannelImageUrl = item.Result.ChannelImageUrl,
        };
        _core.Config.Channels.Add(ch);
        _core.Config.Save();
        _core.FollowItems.Add(new FollowItem(ch));
        _core.RefreshNow();
        HintText.Text = $"✔ {ch.ChannelName} 추가됨 — 계속 검색하거나 닫기를 누르세요";
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e) => Close();
}
