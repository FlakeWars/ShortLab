# Dokument wymagań produktu (PRD) - ShortLab: automatyczny system generowania i publikacji Shorts oparty o AI
## 1. Przegląd produktu
1. Cel: Zbudować eksperymentalny, lokalny system, który codziennie generuje, renderuje i publikuje krótkie animacje 2D typu Short, aby empirycznie sprawdzić, czy regularna publikacja treści AI zwiększa zasięgi w rolling 14-dniowych oknach.
2. Zakres MVP: Półautomatyczny pipeline oparty o kolejkę zadań i workerów, z webowym panelem review, deterministycznym renderem 2D oraz zbieraniem metryk z YouTube i TikTok.
3. Charakter animacji: Minimalistyczne, krótkie, deterministyczne symulacje 2D oparte o FSM i predefiniowane reguły, z ograniczoną paletą kolorów i prostą kompozycją.
4. Architektura: Lokalne uruchomienie, job-based pipeline: generacja DSL -> render -> QC/review -> publikacja -> metryki -> analiza.
5. Autonomia: Etapy manual -> assisted -> semi-auto, z ewaluacją co 14 dni i jawnie zdefiniowanymi kryteriami wyjścia.

## 2. Problem użytkownika
1. Brak skalowalnego sposobu na codzienną publikację Shorts i systematyczną obserwację wpływu regularności na zasięgi.
2. Trudność w utrzymaniu spójnego procesu generacji, kontroli jakości i publikacji przy minimalnym udziale człowieka.
3. Brak deterministycznej reprodukowalności wygenerowanych animacji do analizy i debugowania.
4. Ograniczona możliwość agregacji metryk i analizy trendów w rolling oknach dla wielu platform.
5. Potrzeba bezpiecznego, kontrolowanego zwiększania autonomii systemu opartego na danych, a nie intuicji.

## 3. Wymagania funkcjonalne
1. Generacja koncepcji i specyfikacji
   1.1. System generuje pomysły animacji i zapisuje je jako deterministyczną specyfikację DSL.
   1.2. DSL jest wersjonowany i kompatybilny wstecz; każda animacja referencjonuje wersję DSL.
   1.3. Logika animacji oparta o FSM jako kontrakt API; AI parametryzuje predefiniowane stany i przejścia.
   1.4. (Opcjonalnie) System proponuje kilka krótkich opisów pomysłów; operator wybiera jeden do renderu (Idea Gate).
   1.5. System sprawdza unikalność pomysłu względem historii (hash + similarity/embedding) i oznacza zbyt podobne.
2. Rendering i reprodukowalność
   2.1. System renderuje animacje 2D w formacie pionowym (Short) z określoną długością.
   2.2. Render jest deterministyczny i możliwy do odtworzenia 1:1 z metadanych.
   2.3. Każdy render zapisuje komplet metadanych: seed, wersja DSL, wersja design systemu, parametry symulacji.
3. Design system i warstwa wizualna
   3.1. Warstwa wizualna jest minimalistyczna i oparta o zamrożony Design System MVP.
   3.2. Design System jest wersjonowany i przypisywany do każdej animacji.
4. Pipeline job-based
   4.1. System obsługuje kolejkę zadań i workerów dla etapów: generacja -> (opcjonalnie Idea Gate) -> render -> review -> publikacja -> metryki.
   4.2. Każdy etap zapisuje status i artefakty w repozytorium lokalnym.
   4.3. Niepowodzenia etapów są logowane i możliwe do ponownego uruchomienia.
5. Webowy panel review i QC
   5.1. Panel umożliwia podgląd wideo, metadanych, wersji DSL i Design Systemu.
   5.2. Operator może zaakceptować, odrzucić lub zlecić regenerację.
   5.3. QC zawiera checklisty hard fail i soft judgement; decyzja jest zapisywana z uzasadnieniem.
   5.4. Panel operacyjny pokazuje stan pipeline (queued/running/failed/succeeded) i ostatnie joby.
   5.5. Panel pokazuje listę animacji z filtrami po statusie oraz podstawowe metadane.
   5.6. Panel umożliwia przegląd historii zdarzeń (audit log) z filtrem po typie.
   5.7. Panel zawiera sekcję Idea Gate z propozycjami, wyborem i similarity.
   5.8. Panel udostępnia akcje operacyjne: enqueue, rerun, cleanup jobów.
6. Publikacja
   6.1. System umożliwia półautomatyczny upload na YouTube i TikTok.
   6.2. Publikacja zapisuje identyfikatory materiałów na platformach.
   6.3. System wspiera harmonogram publikacji 1 animacja dziennie.
7. Metryki i analiza
   7.1. System pobiera i agreguje metryki dziennie dla każdej platformy.
   7.2. Metryki są analizowane w oknach 72h, 7 dni i rolling 14 dni.
   7.3. Dane są przechowywane wraz z tagami i metadanymi dla analiz przyczynowych.
8. Tagowanie i archiwizacja
   8.1. System wspiera tagi eksperymentalne i kanoniczne oraz retroaktywne tagowanie.
   8.2. Tylko zaakceptowane animacje są archiwizowane długoterminowo; odrzucone mają TTL 7 dni.
9. Bezpieczeństwo i dostęp
   9.1. Panel review wymaga uwierzytelniania; dostęp ma wyłącznie operator.
   9.2. Zdarzenia audytowe (logowanie, decyzje QC, publikacje) są zapisywane.
10. Eksport i inspekcja danych
   10.1. System umożliwia eksport metadanych i metryk do pliku dla dalszej analizy.
   10.2. System umożliwia podgląd historii decyzji i powiązań między animacjami a wynikami.

## 6. Panel operacyjny (moduł UI)
1. Zakres MVP
   1.1. Dashboard: stan pipeline + ostatnie joby.
   1.2. Animacje: lista + podgląd renderu + metadane.
   1.3. Idea Gate: propozycje + wybór + similarity.
   1.4. QC: decyzje + checklisty.
   1.5. Audit log: przegląd zdarzeń.
2. Akcje
   2.1. Uruchomienie pipeline (enqueue).
   2.2. Rerun renderu.
   2.3. Cleanup jobów (stare running).

## 4. Granice produktu
1. MVP nie obejmuje komercjalizacji ani monetyzacji.
2. MVP nie obejmuje zaawansowanej grafiki 3D ani rozbudowanego sound designu.
3. MVP nie obejmuje pełnej automatyzacji publikacji bez nadzoru człowieka.
4. MVP nie obejmuje zaawansowanej personalizacji treści pod różne segmenty odbiorców.
5. MVP nie obejmuje zautomatyzowanej optymalizacji poprzez A/B testy; jedynie zbieranie danych pod przyszłe testy.
6. Integracja z TikTok może być ograniczona formalnie lub technicznie; w MVP dopuszczalne są manualne obejścia.
7. MVP nie obejmuje wieloużytkowego środowiska z rozbudowanymi rolami i uprawnieniami.

## 5. Historyjki użytkowników
1. US-001
   Tytuł: Generacja codziennej animacji
   Opis: Jako operator chcę wygenerować nową specyfikację DSL dla animacji, aby uruchomić codzienny pipeline.
   Kryteria akceptacji:
   - System generuje DSL i zapisuje wersję DSL oraz metadane generacji.
   - Status zadania jest widoczny w kolejce.
2. US-002
   Tytuł: Render deterministyczny
   Opis: Jako operator chcę wyrenderować animację na podstawie DSL, aby uzyskać gotowy materiał wideo.
   Kryteria akceptacji:
   - Render kończy się plikiem wideo w formacie pionowym.
   - Metadane renderu zawierają seed, wersję DSL i wersję Design Systemu.
3. US-003
   Tytuł: Podgląd materiału
   Opis: Jako operator chcę obejrzeć wyrenderowaną animację w panelu review, aby ocenić jakość.
   Kryteria akceptacji:
   - Panel wyświetla wideo oraz podstawowe metadane.
   - Możliwe jest odtworzenie wideo w całości w przeglądarce.
4. US-004
   Tytuł: Decyzja QC
   Opis: Jako operator chcę zaakceptować lub odrzucić animację na podstawie checklisty QC, aby kontrolować jakość.
   Kryteria akceptacji:
   - Można wybrać wynik: akceptacja lub odrzucenie.
   - Decyzja wymaga wskazania powodów hard fail lub soft judgement.
5. US-005
   Tytuł: Regeneracja animacji
   Opis: Jako operator chcę zlecić regenerację, gdy animacja nie spełnia kryteriów, aby otrzymać alternatywę.
   Kryteria akceptacji:
   - Regeneracja tworzy nowy rekord animacji z unikalnym ID.
   - Poprzedni rekord zachowuje historię decyzji QC.
6. US-006
   Tytuł: Publikacja na YouTube
   Opis: Jako operator chcę opublikować zaakceptowany materiał na YouTube, aby rozpocząć zbieranie metryk.
   Kryteria akceptacji:
   - System zapisuje ID materiału z YouTube.
   - Status publikacji jest widoczny w panelu.
7. US-007
   Tytuł: Publikacja na TikTok
   Opis: Jako operator chcę opublikować zaakceptowany materiał na TikTok, aby zebrać metryki.
   Kryteria akceptacji:
   - System zapisuje ID materiału z TikTok.
   - W przypadku braku integracji system umożliwia ręczne potwierdzenie publikacji.
8. US-008
   Tytuł: Harmonogram dzienny
   Opis: Jako operator chcę uruchamiać pipeline raz dziennie, aby spełnić wymóg 1 animacji dziennie.
   Kryteria akceptacji:
   - System pozwala ustawić dzienne okno publikacji.
   - Historia uruchomień jest dostępna w panelu.
9. US-009
   Tytuł: Pobieranie metryk dziennych
   Opis: Jako analityk chcę pobierać metryki z platform codziennie, aby analizować trendy.
   Kryteria akceptacji:
   - System zapisuje dzienne metryki per platforma.
   - Braki danych są oznaczone w logach.
10. US-010
    Tytuł: Analiza KPI w oknach czasowych
    Opis: Jako analityk chcę widzieć KPI w oknach 72h i 7 dni oraz rolling 14 dni, aby ocenić trend.
    Kryteria akceptacji:
    - System wylicza średnie wyświetlenia i % obejrzenia dla 7 dnia.
    - System wyświetla trend dla rolling 14 dni.
11. US-011
    Tytuł: Tagowanie animacji
    Opis: Jako operator chcę tagować animacje, aby później analizować ich skuteczność.
    Kryteria akceptacji:
    - Możliwe jest dodanie tagów kanonicznych i eksperymentalnych.
    - Tagi można dodać lub zmienić po publikacji.
12. US-012
    Tytuł: Archiwizacja zaakceptowanych animacji
    Opis: Jako operator chcę archiwizować zaakceptowane animacje, aby zachować je do analizy.
    Kryteria akceptacji:
    - Zaakceptowane animacje są przechowywane bezterminowo.
    - Odrzucone animacje są usuwane po 7 dniach.
13. US-013
    Tytuł: Reprodukcja 1:1
    Opis: Jako twórca systemu chcę odtworzyć dowolną animację 1:1, aby debugować i analizować wyniki.
    Kryteria akceptacji:
    - System umożliwia rerender na podstawie zapisanych metadanych.
    - Rerender generuje identyczny wynik przy tym samym seedzie.
14. US-014
    Tytuł: Podgląd historii decyzji
    Opis: Jako operator chcę widzieć historię decyzji QC i publikacji, aby mieć pełny audyt.
    Kryteria akceptacji:
    - Panel pokazuje chronologiczną listę decyzji i statusów.
    - Każde zdarzenie ma znacznik czasu i autora.
15. US-015
    Tytuł: Zarządzanie wersją Design Systemu
    Opis: Jako operator chcę przypisywać wersję Design Systemu do animacji, aby zachować spójność wizualną.
    Kryteria akceptacji:
    - System zapisuje wersję Design Systemu przy renderze.
    - Możliwe jest przeglądanie użytych wersji dla każdej animacji.
16. US-016
    Tytuł: Uwierzytelnianie operatora
    Opis: Jako administrator chcę, aby panel review był dostępny tylko po zalogowaniu, aby ograniczyć dostęp.
    Kryteria akceptacji:
    - Dostęp do panelu wymaga uwierzytelnienia.
    - Nieudane logowania są rejestrowane.
17. US-017
    Tytuł: Eksport danych
    Opis: Jako analityk chcę eksportować metryki i metadane, aby przeprowadzać analizę poza systemem.
    Kryteria akceptacji:
    - System umożliwia eksport do pliku.
    - Eksport zawiera metryki, tagi i podstawowe metadane animacji.
18. US-018
    Tytuł: Obsługa błędów pipeline
    Opis: Jako operator chcę otrzymywać informację o błędach pipeline, aby szybko reagować.
    Kryteria akceptacji:
    - System oznacza zadania jako failed i zapisuje przyczynę.
    - Możliwe jest ponowne uruchomienie nieudanego etapu.
19. US-019
    Tytuł: Konfiguracja platform
    Opis: Jako operator chcę skonfigurować klucze i ustawienia publikacji, aby system mógł publikować materiały.
    Kryteria akceptacji:
    - Panel umożliwia zapisanie konfiguracji per platforma.
    - Brak konfiguracji blokuje publikację i generuje ostrzeżenie.
20. US-020
    Tytuł: Przegląd KPI per platforma
    Opis: Jako analityk chcę widzieć KPI osobno dla YouTube i TikTok, aby porównywać efekty.
    Kryteria akceptacji:
    - System pokazuje KPI w podziale na platformy.
    - Łączny wskaźnik jest oznaczony jako pomocniczy.
21. US-021
    Tytuł: Retencja danych odrzuconych
    Opis: Jako operator chcę mieć pewność, że odrzucone animacje są przechowywane tymczasowo, aby nie zajmowały zasobów.
    Kryteria akceptacji:
    - System usuwa odrzucone animacje po 7 dniach.
    - Usunięcie jest rejestrowane w logu.
22. US-022
    Tytuł: Wybór pomysłu (Idea Gate)
    Opis: Jako operator chcę wybrać jeden z kilku zaproponowanych pomysłów, aby ograniczyć renderowanie nietrafionych animacji.
    Kryteria akceptacji:
    - System pokazuje krótkie opisy 3–5 pomysłów.
    - Operator wybiera jeden do renderowania lub wybiera tryb auto.
23. US-023
    Tytuł: Weryfikacja unikalności pomysłu
    Opis: Jako operator chcę wiedzieć, czy nowy pomysł nie jest zbyt podobny do wcześniejszych.
    Kryteria akceptacji:
    - System wylicza podobieństwo (embedding) do historii.
    - Pomysły zbyt podobne są oznaczane i mogą być odrzucone.

## 6. Metryki sukcesu
1. Primary KPI
   1.1. Średnia liczba wyświetleń po 7 dniach od publikacji, liczona osobno dla YouTube i TikTok.
   1.2. Średni procent obejrzenia po 7 dniach, liczony osobno dla YouTube i TikTok.
2. Metryki wspierające
   2.1. Wyświetlenia po 72h.
   2.2. Trend średniej liczby wyświetleń w rolling 14-dniowych oknach.
   2.3. Tempo publikacji i odsetek zaakceptowanych animacji.
3. Sposób pomiaru
   3.1. Dzienna agregacja metryk.
   3.2. Okna obserwacji: 72h, 7 dni, rolling 14 dni.
   3.3. KPI liczone osobno per platforma, wskaźnik łączny pomocniczy.
4. Kryteria sukcesu MVP
   4.1. Występuje trend wzrostowy średniej liczby wyświetleń w rolling 14-dniowych oknach dla co najmniej jednej platformy.
   4.2. System realizuje codzienną publikację przez minimum 14 kolejnych dni.
5. Lista kontrolna jakości PRD
   5.1. Każda historia użytkownika jest testowalna.
   5.2. Kryteria akceptacji są jasne i konkretne.
   5.3. Zdefiniowano wystarczającą liczbę historyjek do pełnego MVP.
   5.4. Uwzględniono uwierzytelnianie i ograniczenia dostępu.
