# 各游戏作曲团队 QQ 歌手 mid 对照

> 用途：`yt-dlp --flat-playlist "https://y.qq.com/n/ryqq/singer/<MID>"`
> 一次性列出该歌手名下所有官方曲目的 songmid。
> **只认老式路径 `/n/ryqq/singer/<mid>`**，`/n/ryqq_v2/singer/<mid>` 会报 `Unsupported URL`。

## 已知 mid

| 游戏 | 歌手 | QQ singer mid | 备注 |
|------|------|---------------|------|
| 原神 | HOYO-MiX | `001uz8tl04tdL8` | 覆盖官方绝大多数 OST，含陈致逸等共署名曲目；实测 3730 首（去重后） |
| 崩坏星穹铁道 | HOYO-MiX | — | 未验证，采集时先跑一次看条目数是否合理 |

## 通用反查办法

不确定 mid 时，从任一**官方专辑**调 QQ 接口：

```
module = music.musichallAlbum.AlbumInfoServer
method = GetAlbumDetail
param  = {"albumMid": "<ALBUM_MID>"}
```

从返回里取：

- `data.singer.singerList[].mid` → 歌手 mid
- `data.company.name` → **核对出品方是否官方**，防止拿到搬运号
- `data.basicInfo.publishDate` → 发行日期

`GetAlbumDetail` **不返回 songList**，只给 basicInfo / company / singer / extra。

## 采集注意

- 歌手页有同名冲突条目（重制版、重复收录），入库时保留首次出现并去重
- `--flat-playlist` 只列条目不下音频，几分钟可出数千首
- 拿到的 songmid **永久有效**，应落进该游戏的曲库对照表复用，不要每次重搜
