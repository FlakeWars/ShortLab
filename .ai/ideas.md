# Pomysły na Shorts (szkic)

1. Reaktor podziału  
   W centrum ekranu znajduje się pulsujące jądro. Cząstki krążą po orbitach. Gdy dwie zderzą się pod odpowiednim kątem – rozszczepiają się na cztery mniejsze. Mniejsze cząstki są szybsze, ale mniej stabilne. Animacja kończy się, gdy ekran wypełni się „pyłem”.  
   Zakończenie: entropia – brak miejsca na kolejne cząstki.  
   Co zobaczysz: wirujące orbity, serię nagłych rozpadów, drobny „pył” wypełniający kadr.  
   Preview/Reguły: orbit + split (angle threshold), rosnąca liczba obiektów, termination: entropy/coverage.

2. Grawitacyjna klepsydra  
   Dwie komory połączone wąskim gardłem. Kulki spadają w dół, ale co pewien czas grawitacja odwraca się. Przy każdym przejściu przez gardło kulka może się sklonować lub zniknąć.  
   Zakończenie: jedna z komór zostaje całkowicie pusta.  
   Co zobaczysz: regularne „przepływy” kulek i odwrócenia kierunku, pulsujący rytm.  
   Preview/Reguły: gravity flip (time), split/decay na przejściu, termination: emptiness/coverage.

3. Ogród kryształów  
   Z losowych punktów zaczynają wyrastać kryształy zgodnie z regułami wzrostu (jak dyfuzja ograniczona). Kryształy blokują sobie nawzajem przestrzeń.  
   Zakończenie: cała przestrzeń zostaje „zamrożona”.  
   Co zobaczysz: powolne rozrastanie struktur i stopniowe „zamarzanie” kompozycji.  
   Preview/Reguły: spawn + growth, repel/constraints, termination: stability.

4. Ekosystem drapieżnik–ofiara  
   Małe punkty poruszają się chaotycznie. Większe je pożerają, rosnąc. Gdy osiągną zbyt duży rozmiar – rozpadają się.  
   Zakończenie: pozostaje tylko jeden „gatunek”.  
   Co zobaczysz: dynamiczne pościgi, wzrost dużych obiektów i okresowe „eksplozje”.  
   Preview/Reguły: attract/repel, merge + split, termination: population (dominujący gatunek).

5. Labirynt, który sam się buduje  
   Ściany wyrastają dynamicznie, reagując na ruch jednej kropki–wędrowca. Każdy jego ruch powoduje powstanie nowej przeszkody.  
   Zakończenie: wędrowiec zostaje całkowicie uwięziony.  
   Co zobaczysz: narastające ściany i stopniowe zawężanie przestrzeni.  
   Preview/Reguły: trail/memory, constraints, termination: no-move/coverage.

6. Spirala replikacji  
   Jedna cząstka porusza się po spirali. Co pełny obrót – powstaje jej kopia, ale z przesuniętą fazą ruchu.  
   Zakończenie: spirala staje się nieczytelna, wypełnia ekran.  
   Co zobaczysz: regularne „narastanie” spirali i coraz gęstszy wzór.  
   Preview/Reguły: orbit + spawn, termination: coverage.

7. Deszcz decyzji  
   Z góry spadają symbole, które przy zderzeniu z podłożem wybierają lewo lub prawo (jak kulki Galtona). Każde odbicie zmienia kolor.  
   Zakończenie: cała paleta kolorów zostaje zużyta.  
   Co zobaczysz: kaskady ruchu, rozchodzące się ścieżki i ewolucję kolorów.  
   Preview/Reguły: gravity + bounce, color shift, termination: palette used.

8. Komórki pamięci  
   Siatka pól zapamiętuje ostatni obiekt, który je odwiedził. Kolejne obiekty reagują na „pamięć” planszy, zmieniając trajektorie.  
   Zakończenie: plansza osiąga stan stabilny (brak zmian).  
   Co zobaczysz: ślady na siatce i stopniowe uspokojenie ruchu.  
   Preview/Reguły: memory + trails, termination: stability.

9. Czarne dziury  
   Małe punkty krążą. Gdy zbiorą się cztery – zapadają się w czarną dziurę, która przyciąga inne.  
   Zakończenie: zostaje jedna dominująca osobliwość.  
   Co zobaczysz: coraz silniejsze skupienia i „wciąganie” sąsiedztwa.  
   Preview/Reguły: attract + merge, termination: single dominant.

10. Zegar chaosu  
    Wskazówki zegara obracają się z różnymi prędkościami. Ich przecięcia generują nowe obiekty.  
    Zakończenie: tarcza przestaje być widoczna.  
    Co zobaczysz: rytmiczne przecięcia i narastający „szum” obiektów.  
    Preview/Reguły: orbit (multi-speed) + spawn, termination: coverage.

11. Grawitacyjna sieć  
    Punkty łączą się sprężystymi liniami. Zbyt duże naprężenie powoduje pęknięcie i powstanie nowych węzłów.  
    Zakończenie: sieć osiąga maksymalną gęstość.  
    Co zobaczysz: powstawanie połączeń i lokalne pęknięcia.  
    Preview/Reguły: attract/repel, split, termination: density.

12. Migracja pikseli  
    Kolorowe piksele „szukają” podobnych sobie. Z czasem tworzą jednolite obszary.  
    Zakończenie: pełna segregacja kolorów.  
    Co zobaczysz: stopniowe grupowanie kolorów w większe bloki.  
    Preview/Reguły: attract by color, termination: stability.

13. Rój z regułą zdrady  
    Obiekty poruszają się stadnie. Co pewien czas jeden zmienia reguły i „zaraża” innych.  
    Zakończenie: wszyscy przyjmują ten sam wzorzec ruchu.  
    Co zobaczysz: przechodzenie roju w nowy rytm ruchu.  
    Preview/Reguły: align + switch rule, termination: convergence.

14. Grawitacyjny ping-pong  
    Kulki odbijają się między dwoma zakrzywionymi powierzchniami. Każde odbicie może je podzielić lub połączyć.  
    Zakończenie: zostaje tylko jedna kulka lub pył.  
    Co zobaczysz: rytmiczne odbicia i nieregularne zmiany liczby obiektów.  
    Preview/Reguły: bounce + split/merge, termination: single/empty.

15. Symulacja czasu  
    Obiekty zostawiają ślady. Ślady wpływają na przyszłe ruchy obiektów.  
    Zakończenie: ekran całkowicie pokryty historią.  
    Co zobaczysz: warstwy śladów i narastające zagęszczenie.  
    Preview/Reguły: memory + trails, termination: coverage.

16. Miasto automatów  
    Kwadraty budują „budynki” według prostych reguł sąsiedztwa.  
    Zakończenie: miasto osiąga maksymalną wysokość.  
    Co zobaczysz: stopniowe „wyrastanie” bloków w górę.  
    Preview/Reguły: grid growth, termination: max height.

17. Paradoks źródła  
    Źródło generuje obiekty, ale im więcej ich jest, tym wolniej działa.  
    Zakończenie: źródło zatrzymuje się.  
    Co zobaczysz: tempo generacji spadające wraz z zagęszczeniem.  
    Preview/Reguły: spawn rate decay, termination: no new spawns.

18. Grawitacja kolorów  
    Kolory przyciągają się lub odpychają zależnie od barwy.  
    Zakończenie: powstaje jeden dominujący kolor.  
    Co zobaczysz: konwergencję do jednego koloru.  
    Preview/Reguły: attract/repel by color, termination: dominance.

19. Rozpad struktury  
    Idealnie symetryczna figura zaczyna tracić elementy według losowych, ale spójnych reguł.  
    Zakończenie: całkowity rozpad.  
    Co zobaczysz: stopniową utratę symetrii i fragmentację.  
    Preview/Reguły: decay + noise, termination: low structure.

20. Maszyna przewidywań  
    Obiekty próbują przewidzieć ruch innych. Błąd predykcji generuje nowe obiekty.  
    Zakończenie: system staje się nieobliczalny (przepełnienie).  
    Co zobaczysz: narastający chaos i skokowy wzrost liczby obiektów.  
    Preview/Reguły: prediction error -> spawn, termination: overflow.
