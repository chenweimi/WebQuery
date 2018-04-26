# Web Query

## Version
Compatable for Anki 2.1.x ONLY

## Main features
- Search web using provided URL and display during card review. **Search the 1st Field** of current note
- Capture web image as card resource and save into note

[中文说明点这里](https://zhuanlan.zhihu.com/p/32341193)

![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/capture.gif)

## Installation
Use the installation code: 627484806

## Instructions
### Capture Image into Note Field
1. Click on button 'Capture' at the button
2. Crop the region of image
2. Select your note field and save
3. Cropped images will be saved to your resource folder of the profile 

### Capture Text into Note Field
Select text in the web and right click to show context menu and save.

## User Configurations
In the "Options" menu open the configuration dialog:

```json
{
    "image_quality": 50,
    "load_on_question": false,
    "preload": true,
    "provider_urls": [
        [
            "Bing",
            "https://www.bing.com/images/search?q=%s"
        ],
        [
            "Wiki",
            "https://en.wikipedia.org/wiki/?search=%s"
        ],
        [
            "WordRoot",
            "http://www.youdict.com/root/search?wd=%s~~#article"
        ]
    ]
}
```

- **image_quality**: Saved image quality, up to 100, default 50.
- **load_on_question**": change to false if you need web to be queried **/ONLY/** on answers.
- **preload**: Query web even it's invisible.

### Load on Card Interval
Config item "load_when_ivl", defaults to ">=0", this value controls the visibility of Web Query dock widget based on current card's intervals:

- New Card: "==0"
- Review Card: ">0"
- Mixed: ">=0"
- Interval within 3 days: "<=3"

When you're looking at the source:
```Python
eval(str(self.card.ivl) + UserConfig.load_when_ivl)
```
You can see that this actually is implemented by Python "eval" .. so you can even set the value as, 1<= interval <=10 and :
```json
{
"load_when_ivl": " in range(1,10)"
}
```

### Provider URL
This is an URL string you can customize in your settings. By default, 
This addon provide a value for Wikipedia: http://en.wikipedia.org/wiki/wiki.html?search=%s

Please note the "%s" at the end for "search=%s" which mean the parameter where addon will fill during the review.

### Extract Web Elements (CSS Selectors)
Although this addon is powerful enough, but sometimes we need to reference parts
 the web's information and others are not wanted, 
 in this case you can use [Standard CSS2 selector](https://www.w3.org/TR/REC-CSS2/selector.html#q1) 
 syntax to query partially.

**Append** selectors at the last of your provider url, separate by "~~":
```json
[
    "WordRoot",
    "http://www.youdict.com/root/search?wd=%s~~#article"
]
```
Above provider url only return the tag(ID = article) HTML in Web Query.

#### Get Provider URL
You would be able to search the web for more provider URL patterns, or make your own just from your browser address bar:
1. Search images in www.bing.com for keyword "anki"
2. I got the URL like this from browser: https://cn.bing.com/images/search?q=anki&FORM=HDRSC2
3. Replace "anki" with "%s" in the parameters "search?q=anki"
4. The Provider URL is https://cn.bing.com/images/search?q=%s&FORM=HDRSC2

![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/url_provider.png)

#### Update Provider URL
**Every Provider URL** should have and only one '%s' place holder.

1. Go to "Tool" > "Addons" and find "WebQuery"
2. Click on "Settings"
3. Find item "provider_urls", you can fill as much as you want, those multiple items will be shown in tabs:
```json
"provider_urls": [
    [
      "Bing",
      "https://www.bing.com/images/search?q=%s"
    ],
    [
      "Wiki",
      "https://en.wikipedia.org/wiki/?search=%s"
    ]
  ],
```
#### Toggle Tab Visibility
Just in case you have plenty of url providers and there must to be many tabs on the widget, you can set visibilities of those tabs to each **NOTE TYPE**, by default they are all turned on for all.

1. Go to menu "Tool" > "Manage Note Types" > Select one note
2. Click on button "Web Query Tab Visibility"
3. Check the visibilities for each of the provider url:

![](https://raw.githubusercontent.com/upday7/WebQuery/master/screenshots/tab_visibility_ck2.png)

### More Provider URL
<em>Speical thanks to @语言-Rahanande for collection</em>
<ul>
    <li><strong>Wikipedia</strong>: <a href="http://en.wikipedia.org/wiki/wiki.html?search=%s" rel="nofollow">http://en.wikipedia.org/wiki/wiki.html?search=%s</a>
    </li>
    <li><b>Bing Image Search</b>: <a href="https://cn.bing.com/images/search?q=%s" rel="nofollow">https://cn.bing.com/images/search?q=%s
    </a></li>
    <li><b> 人人词典</b>: <a href="http://www.91dict.com/words?w=%s " rel="nofollow">http://www.91dict.com/words?w=%s </a>
    </li>
    <li><b> DWDS德语词典</b>: <a href="https://www.dwds.de/wb/%s " rel="nofollow">https://www.dwds.de/wb/%s </a></li>
    <li><b> littre法语词典</b>: <a href="https://www.littre.org/definition/%s " rel="nofollow">https://www.littre.org/definition/%s </a>
    </li>
    <li><b> 波斯语词典</b>: <a href="https://www.vajehyab.com/?q=%s " rel="nofollow">https://www.vajehyab.com/?q=%s </a></li>
    <li><b> naver韩语汉字词典（其余韩汉/韩英、韩日同理）</b>: <a href="http://hanja.naver.com/search?query=%s " rel="nofollow">http://hanja.naver.com/search?query=%s </a>
    </li>
    <li><b> 漢語多功能字庫</b>: <a href="http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/search.php?word=%s " rel="nofollow">http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/search.php?word=%s </a>
    </li>
    <li><b> 拓本文字资料库</b>: <a href="http://coe21.zinbun.kyoto-u.ac.jp/djvuchar?query=%s " rel="nofollow">http://coe21.zinbun.kyoto-u.ac.jp/djvuchar?query=%s </a>
    </li>
    <li><b> 国学大师-书法字典（其余字典同理）</b>: <a href="http://shufa.guoxuedashi.com/?sokeyshufa=%s&submit=&kz=70 " rel="nofollow">http://shufa.guoxuedashi.com/?sokeyshufa=%s&submit=&kz=70 </a>
    </li>
    <li><b> 汉越词典摘引</b>: <a href="http://hanviet.org/hv_timchu_ndv.php?unichar=%s " rel="nofollow">http://hanviet.org/hv_timchu_ndv.php?unichar=%s </a>
    </li>
    <li><b> 土耳其语词源词典，基本上来自Nisanyan</b>: <a href="https://www.etimolojiturkce.com/kelime/%s " rel="nofollow">https://www.etimolojiturkce.com/kelime/%s </a>
    </li>
    <li><b> Nisanyan土耳其语词源词典</b>: <a href="http://www.nisanyansozluk.com/?k=%s " rel="nofollow">http://www.nisanyansozluk.com/?k=%s </a>
    </li>
    <li><b> 荷兰语词源词典</b>: <a href="http://www.etymologiebank.nl/zoeken/%s " rel="nofollow">http://www.etymologiebank.nl/zoeken/%s </a>
    </li>
    <li><b> 斯瓦希里语汉语词典</b>: <a href="http://siwaxili.com/%s " rel="nofollow">http://siwaxili.com/%s </a></li>
    <li><b> 尼泊尔语词典</b>: <a
            href="http://dsalsrv02.uchicago.edu/cgi-bin/philologic/search3advanced?dbname=turner&query=%s&matchtype=exact&display=utf8"
            rel="nofollow">http://dsalsrv02.uchicago.edu/cgi-bin/philologic/search3advanced?dbname=turner&query=%s&matchtype=exact&display=utf8 </a>
    </li>
    <li><b> 尼泊尔语词源词典</b>: <a href="http://dsalsrv02.uchicago.edu/cgi-bin/app/schmidt_query.py?qs=%s&searchhws=yes "
                             rel="nofollow">http://dsalsrv02.uchicago.edu/cgi-bin/app/schmidt_query.py?qs=%s&searchhws=yes </a>
    </li>
    <li><b> CHGIS 哈佛中国历史地理GIS数据库</b>: <a href="http://maps.cga.harvard.edu/tgaz/placename?fmt=html&n=%s "
                                         rel="nofollow">http://maps.cga.harvard.edu/tgaz/placename?fmt=html&n=%s </a>
    </li>
    <li><b> 中国数字植物标本馆</b>: <a href="http://www.cvh.ac.cn/ppbc/%s " rel="nofollow">http://www.cvh.ac.cn/ppbc/%s </a></li>
    <li><b> 中国自然标本馆</b>: <a href="http://www.cfh.ac.cn/Spdb/spsearch.aspx?aname=%s " rel="nofollow">http://www.cfh.ac.cn/Spdb/spsearch.aspx?aname=%s </a>
    </li>
    <li><b> 中国植物志</b>: <a href="http://frps.eflora.cn/frps?id=%s " rel="nofollow">http://frps.eflora.cn/frps?id=%s </a>
    </li>
    <li><b> 中国植物图像库</b>: <a href="http://www.plantphoto.cn/list?keyword=%s" rel="nofollow">http://www.plantphoto.cn/list?keyword=%s</a>
    </li>
</ul><a href="https://cn.bing.com/images/search?q=%s" rel="nofollow"></a>
