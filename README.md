BUILD BUILD MY DOLL AND PILLOW AND RECORDER
FROM XIAOZHI-ESP, REBUILD TO MICROPYTHON FROM C++.
不过，话说回来，看来是得稍微抽象抽象了对象了并构建整体端侧逻辑了。

唉，流水线。

# 1、
    pip install mpremote
# 2、
    执行pipline/deploybuilder.py
    会生成deploy.json,并上传相关文件；
    相关需要构建上传的文件规则见builder代码；
# 3、
    在设备上运行deploy.py，按照json中的记录，进行文件文件目录部署。

先这样。