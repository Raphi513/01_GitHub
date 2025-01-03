# 250101_TopoTrimTool_GUI_+_XYZ_+_GML_(V20)

# Import-Module
import os
import requests
import zipfile
import customtkinter as ctk
import threading
from tkinter import messagebox
import webbrowser
import json
import datetime
import urllib
import regex as re
import geopandas as gp
from lxml import etree

# Funktionen Terrain + allgemein ____________________________________________________________________________________________________________
# Funktion zur Berechnung der Kombinationen
def berechne_kombinationen(west, ost, sued, nord):
    west_prefix = str(west)[:4]
    ost_prefix = str(ost)[:4]
    sued_prefix = str(sued)[:4]
    nord_prefix = str(nord)[:4]
    kombinationen = set()
    kombinationen.add(f"{west_prefix}_{sued_prefix}")
    kombinationen.add(f"{west_prefix}_{nord_prefix}")
    kombinationen.add(f"{ost_prefix}_{sued_prefix}")
    kombinationen.add(f"{ost_prefix}_{nord_prefix}")
    return kombinationen

# Funktion zur Bereinigung und Erstellung des Ordners
def ensure_clean_directory(directory):
    if os.path.exists(directory):
        if os.listdir(directory):  # Ordner nicht leer
            counter = 1
            new_directory = f"{directory}_(-{counter})"
            while os.path.exists(new_directory):
                counter += 1
                new_directory = f"{directory}_(-{counter})"
            os.rename(directory, new_directory)
            print(f"Der Ordner '{directory}' wurde umbenannt in '{new_directory}'")
        else:  # Leerer Ordner
            os.rmdir(directory)
            print(f"Leerer Ordner '{directory}' wurde gelöscht.")
    os.makedirs(directory, exist_ok=True)
    print(f"Neuer Ordner erstellt: {directory}")

# Funktion zum Einlesen der Datei
def read_file(input_file):
    with open(input_file, 'r') as f:
        return f.readlines()[1:]  # Ignoriere die Header-Zeile

# Funktion zum Schreiben der Datei
def write_file(output_file, points):
    with open(output_file, 'w') as f:
        f.write("X Y Z\n")
        for x, y, z in points:
            f.write(f"{x} {y} {z}\n")

# Funktion zum Herunterladen der Datei
def download_file(lv95_x, lv95_y, download_folder, raster_spacing):
    base_url = "https://data.geo.admin.ch/ch.swisstopo.swissalti3d"
    current_year = 2026

    while current_year >= 2010:
        api_url = f"{base_url}/swissalti3d_{current_year}_{lv95_x}-{lv95_y}/swissalti3d_{current_year}_{lv95_x}-{lv95_y}_{raster_spacing}_2056_5728.xyz.zip"
        download_path = os.path.join(download_folder, f"{lv95_x}-{lv95_y}_{current_year}.xyz.zip")

        try:
            response = requests.get(api_url)
            if response.status_code == 200:
                with open(download_path, 'wb') as file:
                    file.write(response.content)
                return download_path
        except Exception as e:
            print(f"Fehler beim Herunterladen: {e}")
        current_year -= 1
    return None

# Funktion zum Entpacken der Datei
def unzip_file(zip_file):
    extracted_files = []
    if zipfile.is_zipfile(zip_file):
        with zipfile.ZipFile(zip_file, 'r') as zf:
            zf.extractall(os.path.dirname(zip_file))
            extracted_files.extend(zf.namelist())
        os.remove(zip_file)
    return [os.path.join(os.path.dirname(zip_file), f) for f in extracted_files]

# Funktion zum Kombinieren mehrerer Dateien
def combine_files(input_files, output_file):
    combined_points = []
    for file in input_files:
        lines = read_file(file)
        for line in lines:
            x, y, z = map(float, line.strip().split())
            combined_points.append((x, y, z))
    write_file(output_file, combined_points)

# Funktion zum Filtern der Punkte
def filter_points(points, min_x, max_x, min_y, max_y):
    return [
        (x, y, z) for x, y, z in points
        if min_x <= x <= max_x and min_y <= y <= max_y
    ]

# Funktion zum Entfernen eines Lochs
def remove_hole(points, hole_min_x, hole_max_x, hole_min_y, hole_max_y):
    updated_points = []
    for x, y, z in points:
        if not (hole_min_x <= x <= hole_max_x and hole_min_y <= y <= hole_max_y):
            updated_points.append((x, y, z))
    return updated_points

# Funktion zur Koordinatenbeschneidung
def crop_coordinates(input_file, min_x, max_x, min_y, max_y, add_hole, hole_min_x, hole_max_x, hole_min_y, hole_max_y):
    lines = read_file(input_file)
    points = [(float(x), float(y), float(z)) for x, y, z in (line.strip().split() for line in lines)]
    filtered_points = filter_points(points, min_x, max_x, min_y, max_y)

    if add_hole == "ja" and all(val is not None for val in [hole_min_x, hole_max_x, hole_min_y, hole_max_y]):
        filtered_points = remove_hole(filtered_points, hole_min_x, hole_max_x, hole_min_y, hole_max_y)

    output_file = os.path.splitext(input_file)[0] + "_beschnitten.xyz"
    write_file(output_file, filtered_points)
    print(f"Ausgabedatei erstellt: {output_file}")
    
    if os.path.exists(input_file):
        os.remove(input_file)
        print(f"Die kombinierte Datei '{input_file}' wurde gelöscht.")
    
    # Hohe Auflösung in einem inneren Ausschnitt
    if add_hole == "ja":
        execute_again = "ja" 
        if execute_again == "ja":
            nullfuenf_kombinationen = berechne_kombinationen(hole_min_x, hole_max_x, hole_min_y, hole_max_y)
            nullfuenf_lv95_inputs = nullfuenf_kombinationen
            
            # Erstellen des festen Ordnerpfad unter Downloads
            main_folder = os.path.join(os.path.expanduser("~"), "Downloads", "SwissAlti3D-Dateien")
            nullfuenf_download_folder = os.path.join(main_folder, "innerer_hochauflösender_Ausschnitt")
            os.makedirs(nullfuenf_download_folder, exist_ok=True)  # Ordner erstellen, falls er nicht existiert
            
            # Download + Entzippen der inneren Ausschnitts-Dateien
            all_extracted_files = []
            for lv95_pair in nullfuenf_lv95_inputs:
                lv95_x, lv95_y = map(int, lv95_pair.split('_'))
                nullfuenf_download_path = download_file(lv95_x, lv95_y, nullfuenf_download_folder, '0.5')
                if nullfuenf_download_path:
                    extracted_files = unzip_file(nullfuenf_download_path)
                    all_extracted_files.extend(extracted_files)

            # Zusammenfügen + Beschneiden der inneren Ausschnitts-Datei
            if all_extracted_files:
                combined_file = os.path.join(nullfuenf_download_folder, "Terrain_0_5_kombiniert.xyz")
                combine_files(all_extracted_files, combined_file)
                print(f"Kombinierte Datei erstellt: {combined_file}")

                crop_coordinates(combined_file, hole_min_x, hole_max_x, hole_min_y, hole_max_y, "nein", 1, 2, 3, 4)

# Funktionen Buildings ______________________________________________________________________________________________________________________
# Funktion zum Download des GML-File
def download_file_GML(api_url,Year,Wxxx,Xx,download_folder):
    """
    Lädt eine Datei von der angegebenen URL herunter und speichert sie im Download-Pfad.
    """
    # Zielordner und Datei
    download_path = os.path.join(download_folder, f"{Year}_{Wxxx}-{Xx}.citygml.zip")

    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            with open(download_path, 'wb') as file:
                file.write(response.content)
            print(f"File downloaded successfully to: {download_path}")
            return download_path  # Pfad der heruntergeladenen Datei zurückgeben
        else:
            print(f"Failed to download file. HTTP Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

# Funktion zum Einlesen der GML-Datei
def read_gml_file(input_file):
    try:
        tree = etree.parse(input_file)
        return tree
    except Exception as e:
        raise ValueError(f"Fehler beim Einlesen der Datei {input_file}: {e}")

# Funktion zum Beschneiden von Elementen basierend auf den Koordinaten
def filter_gml(tree, xmin, xmax, ymin, ymax):
    root = tree.getroot()
    ns = {
        "gml": "http://www.opengis.net/gml",
        "bldg": "http://www.opengis.net/citygml/building/2.0",
        "core": "http://www.opengis.net/citygml/2.0"
    }

    def is_within_bounds(coords):
        """Überprüft, ob mindestens eine Koordinate im Bereich liegt."""
        for coord in coords:
            x, y = coord[:2]  # Z ignorieren
            if xmin <= x <= xmax and ymin <= y <= ymax:
                return True
        return False

    def parse_coordinates(pos_list):
        """Konvertiert GML posList oder coordinates in eine Liste von (x, y, z)-Tupeln."""
        coords = pos_list.split()
        coords = [float(c) for c in coords]
        return list(zip(coords[::3], coords[1::3], coords[2::3]))

    # Entfernt Elemente, deren Geometrien vollständig ausserhalb der Begrenzungen liegen
    for element in root.xpath("//gml:posList | //gml:coordinates", namespaces=ns):
        coords = parse_coordinates(element.text)
        if not is_within_bounds(coords):
            parent = element.getparent()
            grandparent = parent.getparent()
            grandparent.remove(parent)
    return tree

# Funktion zum Kombinieren mehrerer GML-Bäume (Dateien)
def merge_gml_trees(trees):
    combined_tree = trees[0]
    combined_root = combined_tree.getroot()

    for tree in trees[1:]:
        root = tree.getroot()
        for element in root:
            combined_root.append(element)

    return combined_tree

# Funktion zum Speichern der gefilterten Datei
def write_gml_file(tree, output_file):
    with open(output_file, 'wb') as f:
        f.write(etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="UTF-8"))
    print(f"Die kombinierte gefilterte Datei wurde gespeichert: {output_file}")


# Main-Funktion Terrain _____________________________________________________________________________________________________________________
def main(raster_choice, min_x, max_x, min_y, max_y, add_hole, hole_min_x, hole_max_x, hole_min_y, hole_max_y):

    # Berechne Kombinationen aus den Eingaben
    kombinationen = berechne_kombinationen(min_x, max_x, min_y, max_y)
    print(f"Generierte Kombinationen: {', '.join(kombinationen)}")

    # Die generierten Kombinationen als Input verwenden
    lv95_inputs = kombinationen
    download_folder = os.path.join(os.path.expanduser("~"), "Downloads", "SwissAlti3D-Dateien")
    ensure_clean_directory(download_folder)

    # Download + Entzippen der Dateien
    all_extracted_files = []
    for lv95_pair in lv95_inputs:
        lv95_x, lv95_y = map(int, lv95_pair.split('_'))
        download_path = download_file(lv95_x, lv95_y, download_folder, raster_choice)
        if download_path:
            extracted_files = unzip_file(download_path)
            all_extracted_files.extend(extracted_files)

    # Zusammenfügen + Beschneiden der Datei
    if all_extracted_files:
        combined_file = os.path.join(download_folder, "Terrain_kombiniert.xyz")
        combine_files(all_extracted_files, combined_file)
        print(f"Kombinierte Datei erstellt: {combined_file}")

        crop_coordinates(combined_file, min_x, max_x, min_y, max_y, add_hole, hole_min_x, hole_max_x, hole_min_y, hole_max_y)

# Main-Funktion Building ____________________________________________________________________________________________________________________
def main_building(min_x, max_x, min_y, max_y):
    # Beschneidungskombinations-Werte
    x=[min_x, max_x]
    y=[min_y, max_y]
    
    download_folder_build = os.path.join(os.path.expanduser("~"), "Downloads", "SwissBuildings_3_0_GML-Dateien") # Ordner wird erstellt
    ensure_clean_directory(download_folder_build) # Ordnerstruktur wird ggf. bereinigt

    # Herunterladen der spezifischen Kacheln durch API-Verbindung
    coord=gp.GeoDataFrame(geometry=gp.points_from_xy(x,y),crs="epsg:2056").to_crs("epsg:4326")["geometry"]
    x_deg=coord.x
    y_deg=coord.y

    response = urllib.request.urlopen("https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissbuildings3d_3_0/items?bbox="+str(round(x_deg[0],7))+","+str(round(y_deg[0],7))+","+str(round(x_deg[1],7))+","+str(round(y_deg[1],7)))
    data_json=json.loads(response.read())
    l=[(x["href"],datetime.datetime.strptime(v["properties"]["datetime"],"%Y-%m-%dT%H:%M:%SZ").year) for v in data_json["features"] for _,x in v["assets"].items()]
    ls=[(x,y,[int(z) for z in re.search("(....)-(..)",x).groups()]) for x,y in l if "gml" in x]
    l2=set([(z[0],z[1]) for _,_,z in ls])
    lf=[]
    for x,y in l2:
        ym=max([b for _,b,c in ls if c[0]==x and c[1]==y])
        lf+=[(a,b,c) for a,b,c in ls if b==ym and c[0]==x and c[1]==y]

    # Download + Entzippen der Dateien
    all_extracted_files = []    
    for a,b,c in lf:
        download_path = download_file_GML(a,b,c[0],c[1], download_folder_build)
        if download_path:
            extracted_files = unzip_file(download_path)
            all_extracted_files.extend(extracted_files)
    
    # Zusammenfügen + Beschneiden der Datei
    input_files = all_extracted_files # ? -> ja
    trees = []
    for input_file in input_files:
        tree = read_gml_file(input_file)
        filtered_tree = filter_gml(tree, min_x, max_x, min_y, max_y)
        trees.append(filtered_tree)

    # Kombiniere alle gefilterten Bäume (Dateien)
    combined_tree = merge_gml_trees(trees)

    # Speicheren der kombinierten Datei
    output_dir = os.path.dirname(input_files[0])
    output_file = os.path.join(output_dir, "Buildings_kombiniert_beschnitten.gml")
    write_gml_file(combined_tree, output_file)


# Ausführung des Hauptskripts________________________________________________________________________________________________________________
# Funktion zur Ausführung des Hauptskripts im Hintergrund (Allgemein + Terrain)
def run_main_in_background(buildings_var_ = "no"):
    # Eingabe aller geforderten Werte/Variablen
    raster_choice = raster_choice_var.get()
    min_x = float(min_x_entry.get())
    max_x = float(max_x_entry.get())
    min_y = float(min_y_entry.get())
    max_y = float(max_y_entry.get())
    add_hole = hole_choice_var.get()
    hole_min_x = float(hole_min_x_entry.get()) if hole_min_x_entry.get().strip() else None
    hole_max_x = float(hole_max_x_entry.get()) if hole_max_x_entry.get().strip() else None
    hole_min_y = float(hole_min_y_entry.get()) if hole_min_y_entry.get().strip() else None
    hole_max_y = float(hole_max_y_entry.get()) if hole_max_y_entry.get().strip() else None

    # Validierung und Anpassung der Lochkoordinaten (nur wenn vorhanden)
    if hole_min_x is not None:
        hole_min_x = max(hole_min_x, min_x + 1)

    if hole_max_x is not None:
        hole_max_x = min(hole_max_x, max_x - 1)

    if hole_min_y is not None:
        hole_min_y = max(hole_min_y, min_y + 1)

    if hole_max_y is not None:
        hole_max_y = min(hole_max_y, max_y - 1)

    # Überprüfen, ob Felder leer sind
    if not min_x or not max_x or not min_y or not max_y:
        messagebox.showerror("Fehler", "Bitte füllen Sie alle Felder aus.")
        return

    # GUI-Ladeanzeige erstellen
    loading_window = ctk.CTkToplevel(root)
    loading_window.title("Laden")
    loading_window.geometry("300x100")
    ctk.CTkLabel(loading_window, text="Daten werden geladen...", font=("Arial", 14)).pack(pady=20)

    # GUI-Fenster als modales Dialogfeld anzeigen
    loading_window.grab_set()

    # Funktion zum Thread starten (Terrain)
    def target():
        try:
            main(raster_choice, min_x, max_x, min_y, max_y, add_hole, hole_min_x, hole_max_x, hole_min_y, hole_max_y)  # Hauptskript ausführen
            messagebox.showinfo("Beendet", "Alle Daten erfolgreich heruntergeladen und in «Downloads» abgespeichert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {e}")
        finally:
            loading_window.destroy()  # Ladeanzeige schliessen
    
    # Funktion zum Thread starten (Terrain + Buildings)
    def target_with_building():
        try:
            main(raster_choice, min_x, max_x, min_y, max_y, add_hole, hole_min_x, hole_max_x, hole_min_y, hole_max_y)  # Hauptskript ausführen
            main_building(min_x, max_x, min_y, max_y)
            messagebox.showinfo("Beendet", "Alle Daten erfolgreich heruntergeladen und in «Downloads» abgespeichert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {e}")
        finally:
            loading_window.destroy()  # Ladeanzeige schliessen

    if buildings_var_ == "no":
        threading.Thread(target=target, daemon=True).start()
    
    if buildings_var_ == "yes":
        threading.Thread(target=target_with_building, daemon=True).start()

# Funktion zur Ausführung des Hauptskripts im Hintergrund (+ Buildings)
def run_main_in_background_with_building():
    buildings_var_ = "yes"
    run_main_in_background(buildings_var_)
    

# GUI (mit Custom TKinter) ________________________________________________________________________________________________________________________
# Funktion zum Öffnen des Links
def open_swisstopo():
    webbrowser.open("https://www.swisstopo.admin.ch/de/hoehenmodell-swissalti3d#swissALTI3D---Download")

# GUI Setup mit customtkinter
ctk.set_appearance_mode("dark")  # Dunkles Design
ctk.set_default_color_theme("dark-blue")  # Farbschema setzen

root = ctk.CTk() 
root.title("TopoTrimTool")  # Programmtitel

# Bildschirmabmessungen abrufen
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Fenstergrösse auf 90 % der Höhe und 45 % der Breite setzen
window_width = int(screen_width * 0.45)
window_height = int(screen_height * 0.91)

# Fensterposition: vertikal zentriert auf der linken Bildschirmhälfte und oben bündig
position_x = 0  # Linke Bildschirmhälfte
position_y = 0  # Oben bündig

root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

# Titel hinzufügen
ctk.CTkLabel(root, text="TopoTrim: Topografie-Datenausschnitte nach Wunsch", font=("Arial", 20, "bold")).pack(pady=(20, 10))


# Feld für Rasterwahl
raster_frame = ctk.CTkFrame(root, width=window_width)
raster_frame.pack(fill="x", pady=(10, 0))

ctk.CTkLabel(raster_frame, text="Punktrasterabstand Terrain wählen (Auflösung):", font=("Arial", 13)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
raster_choice_var = ctk.StringVar(value="")  # Kein Raster standardmässig ausgewählt

def update_hole_frame_state():
    if raster_choice_var.get() == "0.5":
        hole_choice_var.set("nein")  # Lochkoordinatenabfrage auf "Nein" setzen, wenn 0.5 gewählt
        hole_choice_yes.configure(state="disabled")
        hole_choice_no.configure(state="disabled")
        hide_hole_fields()
    elif raster_choice_var.get() == "2":
        hole_choice_yes.configure(state="normal")
        hole_choice_no.configure(state="normal")
    else:
        hide_hole_fields()
    update_run_button_state()

raster_choice_0_5 = ctk.CTkRadioButton(raster_frame, text="0.5 (hochauflösend)", variable=raster_choice_var, value="0.5", command=update_hole_frame_state)
raster_choice_2 = ctk.CTkRadioButton(raster_frame, text="2 (mittelauflösend)", variable=raster_choice_var, value="2", command=update_hole_frame_state)
raster_choice_0_5.grid(row=0, column=1, padx=10, pady=10, sticky="w")
raster_choice_2.grid(row=0, column=2, padx=10, pady=10)


# Box für den SwissTopo-Link
link_frame = ctk.CTkFrame(root, width=window_width)
link_frame.pack(fill="x", pady=(10, 0))

# Beschreibungstext und Link für SwissTopo
description_text = "Öffne die Karte von SwissTopo im Split View für die visuelle Koordinatenauswahl."
swisstopo_label = ctk.CTkLabel(link_frame, text=description_text, font=("Arial", 13), anchor="w") # font=("Arial", 13)
swisstopo_label.pack(side="left", padx=10, pady=5)

# Link-Button für SwissTopo
link_button = ctk.CTkButton(link_frame, text="SwissTopo", font=("Arial", 13, "underline", "bold"), fg_color="darkgrey", text_color="white", cursor="hand2", command=open_swisstopo)
link_button.pack(side="left", padx=10)

link_frame_2 = ctk.CTkFrame(root, width=window_width)
link_frame_2.pack(fill="x", pady=(10, 0))

# Beschreibungstext und Link für SwissTopo
description_text_2 = "1.  Wähle beim Auswahlmodus: «Auswahl nach Rechteck» \n\n2.  Zoome zum gewünschten Kartenbereich und klicke auf den Button: «Neues Rechteck» \n\n3.  Ziehe ein Rechteck und übetrage die Koordinaten in die Eingabefelder."
swisstopo_label_2 = ctk.CTkLabel(link_frame_2, text=description_text_2, font=("Arial", 13), anchor="w", justify="left", pady=10) # font=("Arial", 14)
swisstopo_label_2.pack(side="left", padx=10, pady=10)


# Boxen erstellen der Haupt-Koordinaten
main_frame = ctk.CTkFrame(root, width=window_width)
main_frame.pack(fill="x", pady=(10, 0))

def check_coordinates():
    if all([min_x_entry.get().strip(), max_x_entry.get().strip(), min_y_entry.get().strip(), max_y_entry.get().strip()]):
        hole_frame.pack(fill="x", pady=10)
    update_run_button_state()

ctk.CTkLabel(main_frame, text="West-Beschneidungs-Koordinate (X_min):", font=("Arial", 13)).grid(row=1, column=0, padx=10, pady=0, sticky="w")
min_x_entry = ctk.CTkEntry(main_frame)
min_x_entry.grid(row=1, column=1, padx=40, pady=5)
min_x_entry.bind("<KeyRelease>", lambda event: check_coordinates())

ctk.CTkLabel(main_frame, text="Ost-Beschneidungs-Koordinate (X_max):", font=("Arial", 13)).grid(row=2, column=0, padx=10, pady=0, sticky="w")
max_x_entry = ctk.CTkEntry(main_frame)
max_x_entry.grid(row=2, column=1, padx=10, pady=5)
max_x_entry.bind("<KeyRelease>", lambda event: check_coordinates())

ctk.CTkLabel(main_frame, text="Süd-Beschneidungs-Koordinate (Y_min):", font=("Arial", 13)).grid(row=3, column=0, padx=10, pady=0, sticky="w")
min_y_entry = ctk.CTkEntry(main_frame)
min_y_entry.grid(row=3, column=1, padx=10, pady=5)
min_y_entry.bind("<KeyRelease>", lambda event: check_coordinates())

ctk.CTkLabel(main_frame, text="Nord-Beschneidungs-Koordinate (Y_max):", font=("Arial", 13)).grid(row=4, column=0, padx=10, pady=0, sticky="w")
max_y_entry = ctk.CTkEntry(main_frame)
max_y_entry.grid(row=4, column=1, padx=10, pady=5)
max_y_entry.bind("<KeyRelease>", lambda event: check_coordinates())

# Box für inneren Ausschnitt
hole_frame = ctk.CTkFrame(root, width=window_width)

ctk.CTkLabel(hole_frame, text="Hohe Datenauflösung im Zentrumsbereich?     ", font=("Arial", 13)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
hole_choice_var = ctk.StringVar(value="nein")  # Standardmässig "Nein" ausgewählt
hole_choice_yes = ctk.CTkRadioButton(hole_frame, text="Ja", variable=hole_choice_var, value="ja", command=lambda: update_hole_fields())
hole_choice_no = ctk.CTkRadioButton(hole_frame, text="Nein", variable=hole_choice_var, value="nein", command=lambda: hide_hole_fields())
hole_choice_yes.grid(row=0, column=1, padx=10, pady=10, sticky="w")
hole_choice_no.grid(row=0, column=2, padx=10, pady=10)

# Zusätzliche Koordinateneingabefelder für inneren Ausschnitt
hole_coordinates_frame = ctk.CTkFrame(root, width=window_width)

def update_hole_fields():
    hole_coordinates_frame.pack(fill="x", pady=0) # pady=10)
    update_run_button_state()

def hide_hole_fields():
    for field in [hole_min_x_entry, hole_max_x_entry, hole_min_y_entry, hole_max_y_entry]:
        field.delete(0, ctk.END)
    hole_coordinates_frame.pack_forget()
    update_run_button_state()

ctk.CTkLabel(hole_coordinates_frame, text="4.  Vorgang für inneren Ausschnitt wiederholen:", font=("Arial", 13)).grid(row=1, column=0, padx=10, pady=5, sticky="w")

# Boxen erstellen der inneren-Ausschnitt-Koordinaten
ctk.CTkLabel(hole_coordinates_frame, text="West-Ausschnitt-Koordinate (X_min):", font=("Arial", 13)).grid(row=2, column=0, padx=10, pady=0, sticky="w")
hole_min_x_entry = ctk.CTkEntry(hole_coordinates_frame)
hole_min_x_entry.grid(row=2, column=1, padx=10, pady=5)
hole_min_x_entry.bind("<KeyRelease>", lambda event: update_run_button_state())

ctk.CTkLabel(hole_coordinates_frame, text="Ost-Ausschnitt-Koordinate (X_max):", font=("Arial", 13)).grid(row=3, column=0, padx=10, pady=0, sticky="w")
hole_max_x_entry = ctk.CTkEntry(hole_coordinates_frame)
hole_max_x_entry.grid(row=3, column=1, padx=10, pady=5)
hole_max_x_entry.bind("<KeyRelease>", lambda event: update_run_button_state())

ctk.CTkLabel(hole_coordinates_frame, text="Süd-Ausschnitt-Koordinate (Y_min):", font=("Arial", 13)).grid(row=4, column=0, padx=10, pady=0, sticky="w")
hole_min_y_entry = ctk.CTkEntry(hole_coordinates_frame)
hole_min_y_entry.grid(row=4, column=1, padx=10, pady=5)
hole_min_y_entry.bind("<KeyRelease>", lambda event: update_run_button_state())

ctk.CTkLabel(hole_coordinates_frame, text="Nord-Ausschnitt-Koordinate (Y_max):", font=("Arial", 13)).grid(row=5, column=0, padx=10, pady=0, sticky="w")
hole_max_y_entry = ctk.CTkEntry(hole_coordinates_frame)
hole_max_y_entry.grid(row=5, column=1, padx=10, pady=5)
hole_max_y_entry.bind("<KeyRelease>", lambda event: update_run_button_state())

# Label für "Development: Julius Tillmetz + Raphael Grob" unten rechts hinzufügen
developer_label = ctk.CTkLabel(
    root,
    text="  Development: Julius Tillmetz + Raphael Grob  ",
    font=("Arial", 10),
    anchor="e"  # Text rechtsbündig ausrichten
)

developer_label.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=0)  

# Funktion dass Label immer im Vordergrund bleibt
def ensure_label_on_top():
    developer_label.lift()  # In der Z-Ordnung anheben
    root.after(100, ensure_label_on_top)  # Wiederholt alle 100ms

ensure_label_on_top()

# Anzeigen der Ausführungs-Button nur wenn alle Inputs gegeben wurden (Terrain + Buildings)
def update_run_button_with_building_state():
    if raster_choice_var.get() in ["0.5", "2"] and (
        (raster_choice_var.get() == "0.5" and all([min_x_entry.get().strip(), max_x_entry.get().strip(), min_y_entry.get().strip(), max_y_entry.get().strip()])) or
        (hole_choice_var.get() == "ja" and all([hole_min_x_entry.get().strip(), hole_max_x_entry.get().strip(), hole_min_y_entry.get().strip(), hole_max_y_entry.get().strip()])) or
        (hole_choice_var.get() == "nein" and all([min_x_entry.get().strip(), max_x_entry.get().strip(), min_y_entry.get().strip(), max_y_entry.get().strip()]))
    ):
        run_button_with_building.pack(fill="x", pady=(0, 10))  # Direkt unter dem ersten Button platzieren
    else:
        run_button_with_building.pack_forget()

# Anzeigen der Ausführungs-Button nur wenn alle Inputs gegeben wurden (Terrain)
def update_run_button_state():
    if raster_choice_var.get() in ["0.5", "2"] and (
        (raster_choice_var.get() == "0.5" and all([min_x_entry.get().strip(), max_x_entry.get().strip(), min_y_entry.get().strip(), max_y_entry.get().strip()])) or
        (hole_choice_var.get() == "ja" and all([hole_min_x_entry.get().strip(), hole_max_x_entry.get().strip(), hole_min_y_entry.get().strip(), hole_max_y_entry.get().strip()])) or
        (hole_choice_var.get() == "nein" and all([min_x_entry.get().strip(), max_x_entry.get().strip(), min_y_entry.get().strip(), max_y_entry.get().strip()]))
    ):
        run_button.pack(fill="x", pady=(10, 5))
    else:
        run_button.pack_forget()
    update_run_button_with_building_state()

# Button: Skript Ausführen (Terrain)
run_button = ctk.CTkButton(root, text="Terrain-Daten beziehen", hover_color="darkblue", text_color="white", command=run_main_in_background)
run_button.pack_forget()

# Button: Skript Ausführen (Terrain + Buildings)
run_button_with_building = ctk.CTkButton(root, text="Terrain- und Gebäude-Daten beziehen", hover_color="darkblue", text_color="white", command=run_main_in_background_with_building)
run_button_with_building.pack_forget()

# GUI-Fenster starten
root.mainloop()

# Module für zum Erstellen einer .exe-Datei:
# pip install pyinstaller
# pip install auto-py-to-exe
# auto-py-to-exe
# One File
# Windows-Based
# Logo: TT-ico-Datei
# Name: TopoTrim