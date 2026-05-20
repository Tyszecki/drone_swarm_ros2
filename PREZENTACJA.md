# Scenariusz prezentacji online (10–12 minut)

Tak, żeby trafić we wszystkie punkty oceniania i wyglądać profesjonalnie.

## Przed spotkaniem (przygotowanie)

1. **Wszystko ma działać** — zbuduj projekt i przetestuj wszystkie scenariusze (Section 4 README) dzień wcześniej.
2. **Przygotuj 3 terminale**:
   - Terminal 1: `cd ~/drone_swarm_ros2 && source install/setup.bash` — będzie tu launch.
   - Terminal 2: to samo, do `ros2 topic echo`, `ros2 service call`.
   - Terminal 3: to samo, do `ros2 action send_goal`.
   Powieksz czcionki w terminalu (`Ctrl++`) — czytelność > wszystko.
3. **Otwórz w przeglądarce**:
   - Twoje repozytorium GitHub
   - Plik `README.md` na GitHub (renderuje ładnie diagramy)
4. **Otwórz w edytorze** (VS Code lub `nano` w terminalu) pliki:
   - `DroneTelemetry.msg`
   - `GetSwarmStatus.srv`
   - `ExecuteMission.action`
   - `swarm_launch.py`
5. **Wyłącz powiadomienia** w systemie.

> **VS Code w WSL2**: w Ubuntu w katalogu projektu wpisz `code .` — Windows VS Code otworzy projekt z Ubuntu. Wcześniej zainstaluj na Windowsie VS Code i extension "WSL".

---

## Scenariusz wystąpienia

### 1. Wprowadzenie (45 s)

> "Witam. Mój projekt to symulator roju dronów napisany w ROS2 Jazzy.
> Wybrałem ten temat, bo w swojej pracy zawodowej zajmuję się systemami
> bezzałogowymi w sektorze morskim, a docelowo planuję rozwinąć ten kod
> do realnej floty dronów z Jetsonami na pokładzie. Wszystkie wymagane
> elementy — Topics, Launch, Service-Client, własne wiadomości i Actions
> — są zintegrowane w jednym, spójnym scenariuszu operacyjnym."

### 2. Pokaż GitHub i architekturę (1 min)

Pokaz repozytorium. Wskaż:
- README z diagramem architektury
- Dockerfile (pokazuje konteneryzację)
- Strukturę katalogów: dwa pakiety — `drone_interfaces` (CMake, custom msg/srv/action) i `drone_swarm` (Python, węzły)

> "Świadomie rozdzieliłem pakiet z interfejsami od pakietu z węzłami —
> tak buduje się to w produkcji, bo jeden zespół może rozwijać kontrakt
> komunikacyjny, a inny implementację."

### 3. Pokaż własne wiadomości (1.5 min)

Otwórz w edytorze:

**DroneTelemetry.msg** — wyjaśnij:
> "Własna wiadomość telemetrii. Używam standardowego `Header` od ROS2
> dla timestampów oraz `geometry_msgs/Point` dla pozycji — to są
> konwencje ROS2, dzięki którym wiadomość jest kompatybilna z `tf2`
> i innymi narzędziami ekosystemu."

**GetSwarmStatus.srv** — pokaż separator `---`:
> "Service to wzorzec request-response. Powyżej `---` jest zapytanie,
> poniżej odpowiedź. Używam tego, żeby system zewnętrzny mógł zapytać
> 'Czy rój jest gotowy?' i dostać natychmiastową, atomową odpowiedź."

**ExecuteMission.action** — pokaż trzy sekcje:
> "Action ma trzy bloki: Goal, Result i Feedback. Pierwsze dwa to
> żądanie i wynik — jak service. Feedback to dodatkowy strumień
> aktualizacji wysyłany przez serwer DO klienta podczas wykonywania.
> Dlatego akcji używa się do długotrwałych operacji jak lot do punktu
> — operator widzi postęp i może misję anulować."

### 4. Uruchom system przez LAUNCH (45 s)

Terminal 1:
```bash
ros2 launch drone_swarm swarm_launch.py
```

> "Plik launch startuje pięć węzłów: trzy drony, koordynator i Mission
> Control. W realnym systemie każdy z tych węzłów działałby na osobnej
> maszynie — Mission Control na statku, drony na pokładach każdego UAV.
> ROS2 używa DDS, więc po prostu znajdą się przez sieć."

### 5. Pokaż TOPICS (1.5 min)

Terminal 2:
```bash
ros2 node list
```
> "Pięć węzłów działa równolegle."

```bash
ros2 topic list
```
> "Tu widać topiki: trzy telemetrie od dronów, trzy topiki komend, plus
> zbiorczy status roju."

```bash
ros2 topic echo /drone_0/telemetry
```
*(zostaw na 5 s, potem Ctrl+C)*
> "Każdy dron publikuje swoją telemetrię z częstotliwością 2 Hz. Widać
> spadającą baterię i drift pozycji."

```bash
ros2 topic hz /drone_0/telemetry
```
> "Częstotliwość rzeczywiście trzyma się 2 Hz."

```bash
ros2 topic echo /swarm/status --once
```
> "Koordynator agreguje stan całego roju do jednego topika."

### 6. Pokaż SERVICE (1 min)

```bash
ros2 service list | grep swarm
```
```bash
ros2 service call /swarm/get_status drone_interfaces/srv/GetSwarmStatus "{include_detailed_telemetry: true}"
```
> "Synchronicznie odpytuję koordynatora — dostaję natychmiast snapshot
> z gotowością misyjną. W realnym systemie to wywoła system planowania
> misji przed wydaniem rozkazu."

### 7. Pokaż ACTION (2 min) — gwóźdź programu

Terminal 3:
```bash
ros2 action send_goal /execute_mission drone_interfaces/action/ExecuteMission \
  "{drone_id: 0, target_position: {x: 20.0, y: 20.0, z: 15.0}, max_speed: 5.0}" \
  --feedback
```

> "Wysyłam Mission Control zadanie: dron 0 ma lecieć do punktu (20, 20, 15)."

Pokaż jak feedback płynie na żywo:
> "Tu widać feedback w czasie rzeczywistym — postęp, aktualna pozycja,
> dystans do celu. Mission Control monitoruje topik telemetrii drona i
> przelicza postęp. Po dotarciu — Result z czasem trwania misji."

Pokaż wynik:
> "Dron dotarł w X sekund. Akcja zwraca strukturalny wynik."

(Opcjonalnie) Pokaż jak Coordinator równolegle widzi zmieniającą się pozycję:
W terminalu 2:
```bash
ros2 topic echo /drone_0/telemetry --once
```

### 8. Docker (45 s)

Pokaż `Dockerfile` i `docker-compose.yml`:

> "Cały system jest zkonteneryzowany. Komenda `docker compose up`
> buduje obraz oparty na oficjalnym `ros:jazzy` i uruchamia rój w
> izolowanym środowisku. To kluczowe dla wdrożenia na Jetsonach — ten
> sam Dockerfile uruchomi się na ARM64 bez zmian, więc deploy na
> realny dron sprowadza się do `docker pull` i `docker run`."

### 9. Roadmapa rozwoju (45 s)

> "Świadomie zaprojektowałem architekturę tak, żeby była podstawą pod
> realny system. Punkty rozwoju:
> 1. Wymiana symulacji w `drone_node.py` na integrację z MAVROS — wtedy
>    węzeł komenderuje realnym PX4 przez MAVLink.
> 2. Konwersja współrzędnych z lokalnego ENU na WGS84 dla operacji
>    GPS-owych.
> 3. Rozproszone wdrożenie: każdy Jetson uruchamia ten sam kontener,
>    a DDS po sieci znajdzie wszystkie węzły automatycznie.
> 4. Dodatkowe akcje: powrót do bazy, formacja, follow-the-leader.
>
> Kontrakt API — wiadomości, serwisy, akcje — pozostaje ten sam.
> Dlatego ROS2 jest standardem w robotyce."

### 10. Q&A (reszta czasu)

---

## Przewidywane pytania prowadzącego

**Q: Dlaczego rozdzieliłeś interfejsy od węzłów?**
A: Bo interfejsy generowane są przez `rosidl` (CMake), a kod węzłów to Python (`ament_python`). To różne build systemy. Poza tym separacja kontrakt/implementacja to dobra praktyka — kontrakt może być współdzielony między projektami.

**Q: Czemu MultiThreadedExecutor w mission_control?**
A: Bo `execute_callback` akcji jest blokujący — czeka aż dron doleci. W single-threaded executorze ten blok zablokowałby też subskrypcje telemetrii, przez co Mission Control nie wiedziałby gdzie dron jest. Multi-threaded + ReentrantCallbackGroup pozwala wykonywać callbacki równolegle.

**Q: Dlaczego `lambda msg, did=i:` zamiast `lambda msg: f(i)`?**
A: Klasyczna pułapka Pythona — `i` w lambdzie byłoby leniwie wiązane, więc wszystkie callbacki używałyby ostatniej wartości `i`. `did=i` zamraża wartość w chwili tworzenia lambdy.

**Q: Co to jest DDS?**
A: Data Distribution Service — middleware sieciowy, którego używa ROS2. Robi automatyczne odkrywanie węzłów w sieci, niezawodną transmisję, QoS. Dzięki temu ten sam kod działa lokalnie i rozproszenie po wielu maszynach.

**Q: Co by się stało, gdyby coordinator padł?**
A: Drony dalej publikują telemetrię i przyjmują komendy — są autonomiczne. Mission Control też działa niezależnie. Tylko zbiorczy widok znika do restartu koordynatora. To celowo, dla odporności.

**Q: Dlaczego ROS2 Jazzy, a nie ROS1 / Foxy / Humble?**
A: Jazzy to obecne LTS na Ubuntu 24.04. ROS1 jest deprecated. Foxy out-of-support. Humble żyje, ale Jazzy ma nowszego DDS i lepsze wsparcie dla rozproszonych systemów.

**Q: Skąd liczba 3 dronów?**
A: To parametr — `ros2 launch drone_swarm swarm_launch.py num_drones:=5` zmieni. Pozycje startowe trzeba dodać do listy w launch (TODO w produkcji: generować je z formacji).

---

## Checklist 5 minut przed startem

- [ ] Komputer podłączony do zasilania
- [ ] Zamknięte zbędne aplikacje
- [ ] Powiększona czcionka w terminalach
- [ ] Otwarte: GitHub w przeglądarce, 3 terminale Ubuntu, VS Code z plikami msg/srv/action
- [ ] Sprawdzone, że `colcon build` przeszedł i `ros2 launch` startuje bez błędów
- [ ] Testowy `ros2 action send_goal` przeszedł
- [ ] Mikrofon/kamera działają (test w aplikacji do spotkań)
