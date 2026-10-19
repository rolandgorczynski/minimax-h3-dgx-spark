# Plakaty po polsku na Facebooka

Workflow `workflows/01_Plakat_Facebook_PL.json` tworzy PNG 1080 × 1350 px.
FLUX.2 Klein 9B BF16 generuje ilustrację bezpośrednio w ComfyUI na lokalnym Sparku. Osobny węzeł nakłada
polskie teksty, oryginalne logo i opcjonalną belkę partnerów. Nie używa chmury.

## Instalacja

Wymaga istniejącej instalacji ComfyUI i następujących lokalnych modeli:

- `models/diffusion_models/flux-2-klein-9b-bf16.safetensors`
- `models/text_encoders/qwen_3_8b.safetensors`
- `models/vae/flux2-vae.safetensors`

Te modele są już przygotowane na tym Sparku z istniejącej lokalnej kopii 9B. W workflow widać standardowe węzły
**UNETLoader**, **CLIPLoader** (typ `flux2`) i **VAELoader**. Główny węzeł używa
lokalnych mechanizmów ComfyUI: kodowania tekstu, Flux2Scheduler, samplera Euler
z czterema krokami i dekodowania VAE. Nie wykonuje żądań HTTP do generatora.

Z katalogu projektu uruchom:

```bash
./scripts/install_posters.sh
docker compose up -d
```

Jeśli ComfyUI już działa, po aktualizacji węzłów uruchom `docker restart minimax-h3-comfyui`.
Instalator kopiuje węzły, logo i workflow do trwałego katalogu danych.
Zmienione dotychczasowe workflowy są przed aktualizacją kopiowane do
`user/default/workflow-backups/<data>/`. Inne projekty nie są zmieniane.

Nie trzeba instalować nowych pakietów, uruchamiać `flux-klein-spark`, tworzyć
sieci `hycanvas-ai` ani podawać klucza API. Starszy plik `user/default/dgx-posters.json`
nie jest już odczytywany. `docker-compose.posters.yml` pozostaje pustą nakładką
zgodności dla dotychczasowych poleceń Compose. Przy aktualizacji otwórz ponownie
wybraną z trzech aktualnych szablonów, aby dodać połączenia lokalnych modeli.
Stare kopie bez podłączonych modeli wyświetlą instrukcję zamiast używać zewnętrznej usługi.

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
W tym trybie nie odbywa się generowanie obrazu. Węzły modeli można odłączyć. Zmiana ziarna daje nowy wariant ilustracji.
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

## Przeniesienie istniejącego 9B do ComfyUI

Nie trzeba ponownie pobierać wag ani uruchamiać osobnego serwisu FLUX.
Gdy model jest zapisany jako snapshot Diffusers z podkatalogami `transformer/`
i `text_encoder/`, przygotuj natywne pliki ComfyUI:

```bash
python3 scripts/prepare_poster_9b.py /sciezka/do/snapshotu/FLUX.2-klein-9B /sciezka/do/ComfyUI/models
./scripts/install_posters.sh
```

Skrypt korzysta wyłącznie ze standardowej biblioteki Pythona. Łączy shardy,
mapuje nazwy tensorów na format ComfyUI, łączy Q/K/V i przestawia kolejność
scale/shift końcowej modulacji. Wagi zachowują dokładność BF16, bez kwantyzacji.
Wymaga około 35 GB dodatkowego miejsca; pliki źródłowe pozostają niezmienione.
Nie nadpisuje istniejących plików docelowych. Wymagany FLUX2 VAE jest wspólny z 4B.
Po instalacji odśwież listę modeli w ComfyUI i otwórz aktualny workflow.
