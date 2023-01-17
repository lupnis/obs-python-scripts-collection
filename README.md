# obs-python-scripts-collection
OBS的Python脚本，绝大多数是B站直播使用，更新中.

## B站粉丝计数条码
#### 版本 : v1
#### 功能 : 设置目标mid，设置刷新间隔，设置锁定控件，其他功能预计下版本更新.
#### 描述 : 本脚本基于flask，通过创建web服务器并修改obs场景中的web浏览器源，实现粉丝实时计数的条码展示.
#### 其他 : obspython无法创建自定义源，因此需要第三方web源来提供自定义窗口.
#### 依赖 : 该插件依赖的python包为 : <code>flask, gevent, requests</code>.

<hr>

## B站直播控制器
#### 版本 : v1
#### 功能 : 账户登录, 自动开关播, 设置直播分类.
#### 描述 : 本脚本基于PyQt5，创建控制窗口进行直播控制，使obs直播也可一键开播.
#### 其他 : 由于api限制(或者是我没看到), 直播的推流地址和密钥需要自行在设置中填写. 具体操作为先在网页端进行一次开播操作, 复制网页上开播后展示的推流地址和密钥并进入**obs>设置>推流**粘贴. 该过程要且仅要操作一次, 后续无需再进行网页端操作.
#### 依赖 : 该插件依赖的python包为 : <code>requests, (PyQt5, pyinstaller为需要自行build核心代码的友友需要引入的库)</code>.
#### **** : 由于脚本的qt和obs的qt存在本人无法解决的冲突崩溃问题, 本脚本提前将窗口打包为可执行程序, 并在脚本部分使用subprocess进行控制. 如果需要修改窗口样式等, 仅需修改<code>./src/conf.ui</code>的内容即可, 在不增/减/重命名控件的情况下无需重新编译核心部分代码. **在这种情况下, 可以把<code>B站直播控制器/wnd_source</code>这个文件夹直接删除, 不影响使用**.
#### **** : 若要重新打包, 请遵循如下步骤:
+ step 0 : 安装所有依赖库.
+ step 1 : 进入<code>wnd_source</code>目录并做好所有修改.
+ step 2 : 将<code>B站直播控制器/wnd_source</code>下的wnd.py使用pyinstaller进行打包操作(指令为<code>pyinstaller wnd.py --noconsole</code>).
+ step 3 : 等待打包完成后, 将生成的<code>dist/wnd</code>文件夹下所有内容(有点多)转移进入src, 请使用覆盖操作以防止src中原有conf.ui丢失
+ step 4 : 自行进行文件清理.
