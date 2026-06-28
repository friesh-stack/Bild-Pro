# Bild-Pro – Windows 10 Bildsortierer

Dies ist die erste echte Desktop-Version für Windows 10.

## Was die App macht

- Fotoordner auswählen
- Ferienwohnung auswählen
- Bilder automatisch nach Kategorien sortieren
- Bilder auf ca. 150–300 KB komprimieren
- 9:16 Hochformat für Handyportale erzeugen
- Originale sichern
- Excel-, CSV- und HTML-Übersicht erstellen

## Start auf Windows 10

1. Python installieren.
2. Im Projektordner doppelt auf `start_windows.bat` klicken.

Oder in der Eingabeaufforderung:

```bat
pip install -r requirements.txt
python main.py
```

## EXE erstellen

Wenn Python und PyInstaller installiert sind:

```bat
build_windows.bat
```

Danach liegt die anklickbare App unter:

```text
dist/Bild-Pro/Bild-Pro.exe
```

## GitHub Desktop

Diese Dateien in den lokalen Ordner `Bild-Pro` kopieren, dann in GitHub Desktop:

1. Summary: `Erste Windows-10-Version`
2. Commit to main
3. Push origin
