# Plakaty po polsku na Facebooka

Workflow `workflows/01_Plakat_Facebook_PL.json` tworzy PNG 1080 × 1350 px.
FLUX.2 Klein 9B generuje ilustrację na lokalnym Sparku. Osobny węzeł nakłada
polskie teksty, oryginalne logo i opcjonalną belkę partnerów. Nie używa chmury.

## Instalacja

Wymaga działającego lokalnego projektu `flux-klein-spark` z API na porcie 7862
oraz sieci Docker `hycanvas-ai`. Model musi być pobrany i załadowany w usłudze FLUX.
Nie trzeba pobierać go ponownie do ComfyUI.

Z katalogu projektu uruchom:

```bash
./scripts/install_posters.sh /home/jee/docker/flux-klein-spark/.env
docker compose -f docker-compose.yml -f docker-compose.posters.yml up -d
```

Instalator kopiuje węzły, logo i workflow do trwałego katalogu danych.
Klucz API zapisuje wyłącznie w `user/default/dgx-posters.json` z prawami 0600.
Nie umieszczaj tego pliku na GitHubie. Istniejąca konfiguracja nie jest nadpisywana.
Adres lokalnego API można zmienić w polu `url` tego pliku.
Przy kolejnych odtworzeniach kontenera używaj obu plików Compose.

## Używanie

1. Otwórz ComfyUI i odśwież stronę. Wybierz **Workflows → Plakaty → 01_Plakat_Facebook_PL**.
2. Wpisz organizatora, tytuł, tematy/prowadzących, datę, godziny i miejsce.
3. Opisz ilustrację. Opis może być po polsku; dla precyzji modelu można użyć angielskiego.
4. Kliknij **Run / Ausführen**. Gotowy PNG pojawi się w podglądzie i `output/plakaty/`.

Logo jest gotowe w węźle **Load Image**. Można zastąpić je innym PNG.
Belka jest opcjonalna: dodaj drugi **Load Image**, połącz IMAGE z `belka`,
a MASK z `maska_belki`. Zalecana belka pozioma o proporcjach przynajmniej 6:1.
Bez podłączonej belki układ wykorzystuje miejsce na treść.

Własne zdjęcie: wyłącz `generuj_obraz` i podłącz IMAGE do `wlasna_ilustracja`.
W tym trybie FLUX i klucz API nie są potrzebne. Zmiana ziarna daje nowy wariant ilustracji.
Ponowne uruchomienie bez zmian może korzystać z pamięci podręcznej ComfyUI.

Data ma format RRRR-MM-DD; dzień tygodnia oblicza program.
Tekst jest dokładnie taki jak wpisany; program nie poprawia nazwisk ani treści.
Zbyt długi tekst kończy się komunikatem zamiast obcięciem napisów.
Ilustracja jest kadrowana do szerokiego pasa; ważne elementy umieszczaj blisko środka.
Szablon ma stałą kompozycję, nie naśladuje dowolnego układu z obrazu referencyjnego.
PNG zawiera workflow bez klucza API i można przeciągnąć go z powrotem do ComfyUI.
Wyjściowy PNG jest rastrowy; teksty zmienia się w polach workflow.

Logo: https://github.com/rolandgorczynski/rkgm/blob/main/RadaKobietGminyMirsk-transparent.png

## Gotowa belka i herb Mirska

Otwórz **Plakaty → 02_Plakat_Facebook_PL_belka_herb**. Oryginalna belka i herb
są już podłączone. Przełączniki `pokaz_belke` i `pokaz_herb` działają niezależnie.
Herb z napisem Gmina Mirsk umieszczany jest w nagłówku, a belka na dole.
Wyłączenie belki zwalnia miejsce na ilustrację. Pliki są kopiowane podczas instalacji
i podczas generowania nie są pobierane z internetu. Własne pliki można wgrać
w odpowiednich węzłach Load Image. Dotychczasowy workflow pozostaje dostępny.

Źródła: [belka](https://github.com/rolandgorczynski/rkgm/blob/main/belka.jpeg),
[herb](https://github.com/rolandgorczynski/rkgm/blob/main/HerbMirsk.jpeg).

## Trzeci workflow: wgrany obraz → vision → plakat

Jednorazowo pobierz model vision:

```bash
./scripts/download_poster_vision.sh
./scripts/install_posters.sh
docker restart minimax-h3-comfyui
```

Otwórz **Plakaty → 03_Plakat_z_obrazka_Vision_PL**. W węźle
**Wgraj obrazek referencyjny** kliknij **Choose file to upload** i wybierz obraz
z komputera. Jest to standardowy węzeł ComfyUI **Load Image**. Przykładowy obraz
jest już wgrany. Internet nie jest potrzebny do pobierania obrazu referencyjnego.

Lokalny [SmolVLM-500M-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM-500M-Instruct)
opisuje scenę po angielsku dla FLUX. Model jest przypięty do rewizji
`a7da5b986cb59b408707209984f360a5f4ad7e47`, przechowywany w
`models/vision/SmolVLM-500M-Instruct` i podczas opisywania nie pobiera nic z internetu.
Działa na CPU, a po opisie zwalnia model. Używa istniejących zależności Transformers,
PyTorch i Pillow. Model może pomijać szczegóły lub błędnie rozpoznawać przedmioty.

Wynik widać w polu podglądu węzła vision i jest podłączony do `opis_z_obrazu`,
który zastępuje ręczne `opis_ilustracji` w głównym węźle.
Pole `poprawiony_opis` pozwala zastąpić odpowiedź modelu własnym tekstem.
Przy pustym polu model generuje opis automatycznie.

Dane wydarzenia wpisuj osobno po polsku. Logo, herb i opcjonalna belka są wstawiane
jako oryginalne pliki. Aby obejrzeć sam opis przed generowaniem obrazu, ustaw główny
węzeł plakatu w tryb **Never** (Ctrl+M), uruchom vision, a następnie włącz ponownie
węzeł plakatu.

Poprzedni węzeł `DGXImageURL` pozostaje zgodny z zapisanymi starszymi projektami,
lecz nie jest używany w trzecim workflow. Akceptuje publiczne linki HTTP/HTTPS
oraz endpoint `/view` lokalnego ComfyUI; limit wynosi 20 MB i 20 megapikseli.
