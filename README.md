# Drone Swarm ROS2 — symulator roju dronów

Projekt zaliczeniowy z ROS2 Jazzy. Demonstruje komunikację między węzłami przy użyciu:

| Wymaganie               | Spełnienie                                          | Punkty |
|-------------------------|-----------------------------------------------------|--------|
| Topics                  | `/drone_N/telemetry`, `/drone_N/cmd_goto`, `/swarm/status` | 3.0    |
| Launch                  | `swarm_launch.py` startuje 5 węzłów jednym poleceniem | +0.5   |
| Service – Client        | `/swarm/get_status` (custom srv)                    | +0.5   |
| Własne wiadomości       | `DroneTelemetry`, `SwarmStatus`, `GetSwarmStatus`, `ExecuteMission` | +0.5   |
| Actions                 | `/execute_mission` z feedbackiem postępu            | +0.5   |
| Docker                  | `Dockerfile` + `docker-compose.yml`                 | bonus  |
| GitHub                  | publiczne repo                                      | bonus  |

**Suma: 5.0**

---

## 1. Architektura

```
                ┌──────────────────────┐
                │  mission_control     │  ◀── Action Server: /execute_mission
                │  (Action Server)     │      (klient → goal → feedback → result)
                └──────────┬───────────┘
                           │ publikuje cele na /drone_N/cmd_goto
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
       ┌─────────┐    ┌─────────┐    ┌─────────┐
       │drone_0  │    │drone_1  │    │drone_2  │   węzły dronów
       │         │    │         │    │         │   (symulują ruch + baterię)
       └────┬────┘    └────┬────┘    └────┬────┘
            │ /drone_N/telemetry           │
            └──────────────┬───────────────┘
                           ▼
                ┌──────────────────────┐
                │ swarm_coordinator    │  ◀── Service: /swarm/get_status
                │ (Subscriber + Srv)   │      Publikuje /swarm/status
                └──────────────────────┘
```

**Dlaczego taka struktura?** Bo to dokładnie wzorzec, którego używa się w prawdziwych systemach multi-UAV (PX4/MAVROS + ROS2). Każdy dron to autonomiczny węzeł publikujący telemetrię, koordynator zbiera całość, a Mission Control wykonuje długotrwałe zadania jako akcje. Po zamianie symulacji ruchu na realny `mavros` ta sama architektura zadziała na Jetsonach.

---

## 2. Instalacja od zera na Windows 11

### Krok 2.1 — Włącz WSL2 i zainstaluj Ubuntu 24.04

1. Otwórz **PowerShell jako Administrator** (Win + X → "Terminal (Administrator)").
2. Wpisz:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
3. Po restarcie komputera Ubuntu samo się uruchomi i poprosi o utworzenie użytkownika (login + hasło, hasło nie wyświetla się przy wpisywaniu — to normalne).
4. Sprawdź wersję:
   ```bash
   lsb_release -a
   ```
   Musi pokazać `Ubuntu 24.04`. ROS2 Jazzy wymaga dokładnie tej wersji.

> **Jak otworzyć Ubuntu później?** W menu Start wpisz "Ubuntu" lub uruchom Windows Terminal → strzałka w dół przy "+" → "Ubuntu".

### Krok 2.2 — Zaktualizuj system

W terminalu Ubuntu:
```bash
sudo apt update && sudo apt upgrade -y
```
Podaj hasło. Czeka się ok. 2-3 min.

### Krok 2.3 — Zainstaluj ROS2 Jazzy

To są oficjalne instrukcje skondensowane. Wklejaj kolejno:

```bash
# 1. Włącz repozytorium "Universe"
sudo apt install -y software-properties-common
sudo add-apt-repository universe

# 2. Dodaj klucz GPG ROS2
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg

# 3. Dodaj repozytorium ROS2
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 4. Instalacja ROS2 Jazzy (wersja desktop)
sudo apt update
sudo apt install -y ros-jazzy-desktop python3-colcon-common-extensions python3-pip git
```

Trwa ~10 minut.

### Krok 2.4 — Automatyczne ładowanie ROS2

Żeby nie wpisywać tego ręcznie przy każdym terminalu:
```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

**Test:**
```bash
ros2 --help
```
Jeśli widzisz pomoc — działa.

---

## 3. Pobranie i zbudowanie projektu

### Krok 3.1 — Skopiuj projekt do Ubuntu

Masz dwie opcje:

**Opcja A: bezpośrednio z GitHub** (po wcześniejszym wgraniu — patrz sekcja 7):
```bash
cd ~
git clone https://github.com/TWOJA_NAZWA/drone_swarm_ros2.git
cd drone_swarm_ros2
```

**Opcja B: rozpakuj ZIP otrzymany od Claude'a**

W Windows masz `drone_swarm_ros2.zip`. Skopiuj go do Ubuntu — najprostsza droga:
1. W eksploratorze Windows wpisz w pasek adresu: `\\wsl$\Ubuntu-24.04\home\TWOJA_NAZWA_UZYTKOWNIKA`
2. Wklej tam ZIP-a.
3. W terminalu Ubuntu:
   ```bash
   cd ~
   sudo apt install -y unzip
   unzip drone_swarm_ros2.zip
   cd drone_swarm_ros2
   ```

### Krok 3.2 — Zbuduj projekt

```bash
# Z katalogu drone_swarm_ros2:
colcon build --symlink-install
```

Pierwszy build trwa ~1-2 min. Powinieneś zobaczyć:
```
Summary: 2 packages finished [XX.Xs]
```

Jeśli colcon nie znajduje `geometry_msgs` lub `action_msgs`:
```bash
sudo apt install -y ros-jazzy-geometry-msgs ros-jazzy-action-msgs
colcon build --symlink-install
```

### Krok 3.3 — Załaduj zbudowane pakiety

```bash
source install/setup.bash
```

> **Wskazówka:** dodaj to do `.bashrc` tylko po zbudowaniu:
> ```bash
> echo "source ~/drone_swarm_ros2/install/setup.bash" >> ~/.bashrc
> ```

---

## 4. Uruchomienie i test

### Krok 4.1 — Uruchom cały rój (Launch)

```bash
ros2 launch drone_swarm swarm_launch.py
```

Powinieneś zobaczyć logi typu:
```
[drone_0]: Dron 0 uruchomiony w pozycji (0.0, 0.0, 10.0)
[drone_1]: Dron 1 uruchomiony w pozycji (5.0, 0.0, 10.0)
[drone_2]: Dron 2 uruchomiony w pozycji (0.0, 5.0, 10.0)
[swarm_coordinator]: Swarm Coordinator nasluchuje 3 dronow...
[mission_control]: Mission Control gotowy. Action server /execute_mission aktywny.
```

**Zostaw to okno otwarte.** Otwórz **drugi terminal Ubuntu** (kolejna karta) do dalszych komend.

W drugim terminalu zawsze najpierw:
```bash
cd ~/drone_swarm_ros2
source install/setup.bash
```

### Krok 4.2 — Test: TOPICS

Lista wszystkich topików:
```bash
ros2 topic list
```
Zobaczysz m.in. `/drone_0/telemetry`, `/drone_1/telemetry`, `/drone_2/telemetry`, `/swarm/status`.

Podejrzyj telemetrię jednego drona:
```bash
ros2 topic echo /drone_0/telemetry
```
(`Ctrl+C` by zatrzymać). Dostaniesz strumień wiadomości typu `drone_interfaces/msg/DroneTelemetry` — Twoja **własna wiadomość**.

Sprawdź zbiorczy stan roju:
```bash
ros2 topic echo /swarm/status
```

### Krok 4.3 — Test: SERVICE

Lista serwisów:
```bash
ros2 service list | grep swarm
```
Zobaczysz `/swarm/get_status`.

Wywołaj serwis:
```bash
ros2 service call /swarm/get_status drone_interfaces/srv/GetSwarmStatus "{include_detailed_telemetry: true}"
```
Odpowiedź:
```
response:
  total_drones: 3
  active_drones: 3
  average_battery: 99.8
  mission_readiness: 100.0
  status_message: 'Roj operacyjny: 3/3 dronow online, gotowosc misyjna 100%'
```

### Krok 4.4 — Test: ACTION

Lista akcji:
```bash
ros2 action list
```
Zobaczysz `/execute_mission`.

Wyślij cel z feedbackiem:
```bash
ros2 action send_goal /execute_mission drone_interfaces/action/ExecuteMission \
  "{drone_id: 0, target_position: {x: 20.0, y: 20.0, z: 15.0}, max_speed: 5.0}" \
  --feedback
```

Zobaczysz **na żywo** strumień feedbacku z postępem (0%, 10%, 25%... aż do 100%), a na końcu wynik z czasem trwania.

### Krok 4.5 — Test: klient programowy (bonus)

W drugim terminalu:
```bash
ros2 run drone_swarm demo_mission_client
```
Klient sam zawoła serwis, a potem wyśle akcję i wypisze feedback w czytelnej formie.

---

## 5. Uruchomienie w Dockerze (bonus)

### Krok 5.1 — Zainstaluj Docker

W Ubuntu pod WSL2:
```bash
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
```
**Wyloguj się i zaloguj** (`exit` i otwórz Ubuntu ponownie), żeby zadziałało bez sudo.

### Krok 5.2 — Zbuduj i uruchom

W katalogu projektu:
```bash
docker compose up --build
```

Pierwsze budowanie trwa ~5 min. Potem cały rój startuje w izolowanym kontenerze.

Żeby wejść do działającego kontenera (np. by wywołać serwis lub akcję):
```bash
docker exec -it drone_swarm bash
# wewnątrz kontenera ROS2 jest już zsourcowany:
ros2 topic list
ros2 service call /swarm/get_status drone_interfaces/srv/GetSwarmStatus "{include_detailed_telemetry: true}"
```

Zatrzymanie: `Ctrl+C` w oknie compose lub `docker compose down`.

---

## 6. Struktura projektu

```
drone_swarm_ros2/
├── Dockerfile                  ← obraz ROS2 Jazzy z workspace
├── docker-compose.yml          ← wygodne uruchomienie
├── entrypoint.sh               ← sourcing przy starcie kontenera
├── README.md                   ← ten plik
├── .gitignore
└── src/
    ├── drone_interfaces/       ← PAKIET CMAKE: msg/srv/action
    │   ├── package.xml
    │   ├── CMakeLists.txt
    │   ├── msg/
    │   │   ├── DroneTelemetry.msg
    │   │   └── SwarmStatus.msg
    │   ├── srv/
    │   │   └── GetSwarmStatus.srv
    │   └── action/
    │       └── ExecuteMission.action
    └── drone_swarm/            ← PAKIET PYTHON: węzły
        ├── package.xml
        ├── setup.py
        ├── setup.cfg
        ├── resource/drone_swarm
        ├── drone_swarm/
        │   ├── __init__.py
        │   ├── drone_node.py            ← N instancji (po jednej na drona)
        │   ├── coordinator_node.py      ← sub + service
        │   ├── mission_control_node.py  ← action server
        │   └── demo_mission_client.py   ← demo programowe
        └── launch/
            └── swarm_launch.py          ← startuje wszystko
```

---

## 7. Wrzucenie na GitHub

```bash
# W katalogu drone_swarm_ros2:
git init
git add .
git commit -m "Initial commit: drone swarm ROS2 simulator"
git branch -M main

# Załóż repo na github.com (z poziomu przeglądarki, bez README), potem:
git remote add origin https://github.com/TWOJA_NAZWA/drone_swarm_ros2.git
git push -u origin main
```

Jeśli git poprosi o login: użyj **Personal Access Token** z GitHub (Settings → Developer settings → Tokens), nie zwykłego hasła.

---

## 8. Rozszerzenie do prawdziwych dronów (przyszłość)

Co konkretnie trzeba zmienić, żeby ten sam kod działał na flocie dronów z Jetsonami:

| Komponent           | Teraz (symulacja)            | Real świat                                  |
|---------------------|------------------------------|---------------------------------------------|
| `drone_node.py`     | symuluje ruch wewnętrznie    | publikuje na `/mavros/setpoint_position/local` i czyta z `/mavros/local_position/pose` |
| Telemetria          | generowana lokalnie          | przychodzi z PX4 przez MAVLink → MAVROS    |
| Pozycje GPS         | x,y,z w metrach              | konwersja WGS84 ↔ ENU (ros2 ma `geographic_msgs`) |
| Komunikacja sieciowa| pojedyncza maszyna           | DDS multicast między Jetsonami przez Wi-Fi/4G/Mesh, ten sam `ROS_DOMAIN_ID` |
| Mission Control     | bez zmian                    | bez zmian — kontrakt API ten sam            |
| Coordinator         | bez zmian                    | bez zmian — kontrakt API ten sam            |

**Architektura zostaje identyczna.** Wymieniasz tylko backend symulacji w `drone_node.py` na integrację z MAVROS, reszta systemu nie zauważy różnicy. To jest sens budowania na ROS2: separacja interfejsów od implementacji.

---

## 9. Przydatne komendy diagnostyczne

```bash
ros2 node list                                    # lista wszystkich węzłów
ros2 node info /drone_0                           # co publikuje/subskrybuje
ros2 topic info /swarm/status                     # typ, publisherzy, subskrybenci
ros2 topic hz /drone_0/telemetry                  # częstotliwość publikacji
ros2 interface show drone_interfaces/msg/DroneTelemetry  # struktura wiadomości
ros2 service type /swarm/get_status               # typ serwisu
ros2 action info /execute_mission                 # info o akcji
rqt_graph                                         # graficzny graf węzłów (po `sudo apt install ros-jazzy-rqt-graph`)
```

---

## Licencja

MIT
