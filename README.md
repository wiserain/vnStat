# vnStat

[vnStat](https://humdi.net/vnstat/) 정보를 보여주는 SJVA 플러그인

## 요구조건

- vnStat 1.18
- vnStat database (/var/lib/vnstat)

기본적으로 이 플러그인은 vnStat로 구축된 트래픽 통계를 **보여줍니다.** 그러므로 vnStat의 설치와 통계 구축은 적어도 아직까지는 직접 하셔야합니다. 

vnStat 버전은 json으로 결과를 출력할 수 있는 1.13+ 이어야하며, 1.18에서 잘 동작함을 확인했습니다. vnStat는 리눅스에서만 사용 가능하므로 윈도우즈는 지원하지 않습니다.  

## 준비과정

여기서는 docker를 통해 SJVA를 운용하고, 호스트(예를 들면 시놀로지)의 트래픽을 모니터링 하는 시나리오를 가정하겠습니다.
 
### 호스트에 vnStat 설치하기

Ubuntu나 Debian, Centos는 각각의 패키지 매니저로 설치해주면 됩니다.

Ubuntu/Debian
```bash
sudo apt update && sudo apt install vnstat
```

Centos
```bash
yum install vnstat
```

시놀로지의 경우 이런 패키지 매니저가 없기 때문에 Entware를 먼저 설치합니다. 과정은 링크로 대신합니다. 

[https://github.com/Entware/Entware/wiki/Install-on-Synology-NAS](https://github.com/Entware/Entware/wiki/Install-on-Synology-NAS)

링크의 설치 과정을 보면 아시겠지만 바인드 마운트한 /opt에 Entware를 설치하기 때문에 이 폴더를 이미 사용중이거나 다른 프로그램 설치를 이미 시도하신 적이 있다면 적절히 삭제 후에 진행해야 합니다. 시스템을 건드리는 부분이니 주의를 요합니다.

설치가 끝나면 opkg를 통해 vnStat 1.18 버전을 설치할 수 있습니다. (설치 직후에는 PATH가 적용되지 않아서 커맨드가 안 먹을 수 있습니다. 쉘 다시 로그인 하거나 속시원하게 재부팅 한번 해주세요.)

```bash
opkg update && opkg install vnstat
```

```vnstat -v```를 ssh 상에 입력해서 버전 정보가 잘 나오는지 확인합니다.

### vnStat 데이터베이스 구축하기

설치 후에는 트래픽 정보를 수집해서 데이터베이스에 기록해야합니다. 먼저 ```ifconfig``` 명령어를 이용해서 모니터링 하고자 하는 네트워크 인터페이스를 선택합니다.

```bash
root@media:~# ifconfig
docker0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 172.17.0.1  netmask 255.255.0.0  broadcast 172.17.255.255
        inet6 fe80::42:ffff:fe47:1eb0  prefixlen 64  scopeid 0x20<link>
        ether 02:42:ff:47:1e:b0  txqueuelen 0  (Ethernet)
        RX packets 1182245  bytes 274598308 (274.5 MB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 2890737  bytes 7887539779 (7.8 GB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

ens192: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.99  netmask 255.255.255.0  broadcast 192.168.1.255
        inet6 fe80::20c:29ff:fe5b:4d8b  prefixlen 64  scopeid 0x20<link>
        ether 00:0c:29:5b:4d:8b  txqueuelen 1000  (Ethernet)
        RX packets 36809845  bytes 48716859087 (48.7 GB)
        RX errors 0  dropped 195  overruns 0  frame 0
        TX packets 5612500  bytes 26018831205 (26.0 GB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1  prefixlen 128  scopeid 0x10<host>
        loop  txqueuelen 1000  (Local Loopback)
        RX packets 180894  bytes 193242493 (193.2 MB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 180894  bytes 193242493 (193.2 MB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
```

다 표시하지 않았지만 도커를 쓴다면 그리고 다양한 가상 네트워크를 쓴다면 이것보다 훨씬 리스트가 길지만 중요한 3개만 표시했습니다. 전 ```ens192```를 호스트 네트워크로 사용하고 있습니다. 여기에 대한 데이터베이스를 먼저 생성해 줍니다.

```bash
vnstat -u -i ens192
```

데이터베이스가 생성되었다고 메시지가 출력될겁니다.

주기적으로 트래픽 정보를 수집하도록 해야 하는데 1) cron으로 x분 마다 실행하거나 2) 같이 제공되는 vnstatd 데몬을 이용하는 방법이 있습니다. vnstatd가 더 낫다고 제작자가 밝히고 있으니 이걸 이용하도록 하겠습니다. 아래의 내용을 cron에 등록하여 시스템 시작시 데몬이 실행될 수 있게 합니다.  

```bash
@reboot /usr/sbin/vnstatd -d
```

시놀로지 유저는 DSM 제어판의 태스크 스케쥴러를 이용하여 아래 명령을 부팅시에 실행하도록 합니다.

```bash
/opt/sbin/vnstatd -d
```

이제 ```/var/lib/vnstat``` (시놀로지 유저는 ```/opt/var/lib/vnstat```) 아래에 네트워크 인터페이스 이름으로 폴더가 만들어지고 정보가 쌓이고 있는 것을 알 수 있습니다.

```bash
$ ls /var/lib/vnstat
br-d654c3591721  veth34dd343  veth81b3562  vethacf1899  vethe9db6a7
docker0          veth39d0924  veth831a8f0  vethc5b60aa  vethee720e7
ens18            veth43915f6  veth92e7e80  vethd3fdad2
```

### 도커에서 vnStat 데이터베이스 가져다 쓰기

네이티브 사용자라면 상관 없지만 도커 사용자라면 이 정보를 볼 수 있게 볼륨매핑을 해줘야 합니다.

```bash
docker run -d \
    --name sjva \
    ...
    -v /var/lib/vnstat:/var/lib/vnstat:ro
    ...
    soju6jan/sjva:0.2
```

이제 거의 다 되었습니다. 

SJVA에 접속해 ```Custom >> vnStat```로 이동하면 에러가 날겁니다. 호스트(예를 들면 시놀로지)에는 vnStat가 설치되었는데 도커 컨테이너에서는 vnStat가 없기 때문이죠. 설정으로 이동하여 설치하기 버튼을 눌러 간편하게 설치할 수 있습니다만, 현재는  docker(alpine x64)와 Ubuntu만 고려되어 있습니다. 다른 배포판의 리눅스 사용자분은 ```SJVA >> 툴``` 메뉴를 이용해서 직접 설치해주세요.

이제 목록 가져오기 버튼을 이용해서 가능한 네트워크 인터페이스를 선택하고 저장하면 트래픽 메뉴에서 업다운 트래픽을 확인할 수 있습니다.

## 읽어보기

- soju6jan님이 시놀로지 사용자를 위해 사진과 함께 설치 방법을 써주셨습니다. [링크](https://soju6jan.com/archives/1219)

## TODO

- 시작시 언제나 vnStat 설치하기 옵션
- ```툴 >> Command```가 disable일 경우 대처
- 트래픽 데이터 수집도 내부 스케줄러를 통해서?
