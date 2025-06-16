2. Ist-Konzept

    2.1 Die Temperatur wird gemessen und, wenn ein kritischer Zustand erreicht wurde wird per Discord eine Benachrichtigung gesendet.
    2.2 Die Luftfeuchtigkeit wird gemessen und, wenn ein kritischer Zustand erreicht wurde wird per Discord eine Benachrichtigung gesendet.
    2.3 Die Helligkeit wird gemessen und, wenn ein kritischer Zustand erreicht wurde wird per Discord eine Benachrichtigung gesendet.
    2.4 Diese drei Datenpunkte werden zum einem auf dem E-Ink-Display angezeigt und entsprechende Liniengraphen werden auf dem LCD Display angezeigt.
    2.5 Bewegungen werden detektiert. Wenn eine Bewegung festgestellt wird, läuft ein Countdown. Innerhalb dieses Countdowns muss die weiße? Karte gescannt werden (siehe 1.6.), um einen Alarm zu verhindern. Ansonsten wird ein auditorische Alarm ausgelöst.
    2.6 Der Kartenscanner erfüllt folgende Funktionen:
        2.6.1 Weiße? Karte     - Alarm verhindern
        2.6.2 Schwarze? Karte  - Programm ausschalten
        2.6.3 Transparte Karte - Doom starten
    2.7 Im Doom Modus wird der Screen auf dem LCD Display gerendert. Der Character kann mit den Dualbuttons bewegt werden und mit dem LED Button kann man die Waffe feuern.
Zustandsdiagramm alarm

    motion detected
    +--------------+
    |              v
 +------+     +-----------+ 
 | idle |     | countdown | -+
 +------+     +-----------+  |
    ^^ card scanned |        |
    |+--------------+        | countdown
    |                        | over
    | card scanned           |
    |                        |
    | +-------+              |
    +-| alarm |<-------------+
      +-------+
       |   ^
       +---+

