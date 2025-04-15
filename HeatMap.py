# (Imports παραμένουν ίδια - pandas, folium, HeatMap, geopy, os, sys, traceback, PyQt6 κλπ)
import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.distance import geodesic
import os
import sys
import traceback
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit,
    QLabel, QFileDialog, QMessageBox, QHBoxLayout
)

# --- Default Configuration (ίδιο) ---
DEFAULT_LAT_CSV_COL = "3"
DEFAULT_LON_CSV_COL = "4"
# ---------------------------

# --- ΕΝΗΜΕΡΩΜΕΝΗ ΣΥΝΑΡΤΗΣΗ με Διόρθωση SyntaxError ---
def process_and_create_maps(file_path, lat_col_index, lon_col_index):
    """
    Διαβάζει το CSV, εξάγει συντεταγμένες, υπολογίζει μέγιστη απόσταση,
    δημιουργεί και αποθηκεύει 4 χάρτες Folium (CircleMarkers με max dist,
    Polyline με dist, Heatmap, Απλές Μπλε Κουκκίδες).

    Args:
        file_path (str): Η διαδρομή προς το αρχείο CSV.
        lat_col_index (int): Ο δείκτης της στήλης CSV για το latitude.
        lon_col_index (int): Ο δείκτης της στήλης CSV για το longitude.

    Returns:
        bool: True αν η διαδικασία ολοκληρώθηκε επιτυχώς, False αλλιώς.
        str: Ένα μήνυμα αποτελέσματος (επιτυχίας ή σφάλματος).
    """
    print("-" * 30)
    print(f"Ξεκινώντας επεξεργασία για: {file_path}")
    print(f"Στήλες CSV: Lat={lat_col_index}, Lon={lon_col_index}")

    base_filename = os.path.basename(file_path)
    filename_without_ext = os.path.splitext(base_filename)[0]
    output_prefix = filename_without_ext.replace(" ", "_").replace(".", "_")
    print(f"Πρόθεμα ονομάτων αρχείων εξόδου: {output_prefix}")

    try:
        # (Η λογική ανάγνωσης CSV και καθαρισμού δεδομένων παραμένει ίδια)
        df = pd.read_csv(file_path, header=None, on_bad_lines='skip', delimiter=",", low_memory=False)
        if df.empty: return False, f"Το αρχείο '{base_filename}' είναι κενό..."
        num_columns = len(df.columns)
        if lat_col_index >= num_columns or lon_col_index >= num_columns: return False, f"Μη έγκυροι δείκτες στηλών..."
        lat_series_str = df.iloc[:, lat_col_index].astype(str).str.strip()
        lon_series_str = df.iloc[:, lon_col_index].astype(str).str.strip()
        latitude_col = pd.to_numeric(lat_series_str, errors='coerce')
        longitude_col = pd.to_numeric(lon_series_str, errors='coerce')
        coords_df = pd.DataFrame({'latitude': latitude_col, 'longitude': longitude_col})
        initial_rows = len(coords_df)
        coords_df.dropna(subset=['latitude', 'longitude'], inplace=True)
        coords_df = coords_df[
            (coords_df['latitude'] >= -90) & (coords_df['latitude'] <= 90) &
            (coords_df['longitude'] >= -180) & (coords_df['longitude'] <= 180)
        ]
        final_rows = len(coords_df)
        print(f"Αρχικές γραμμές CSV: {len(df)}, Γραμμές μετά εξαγωγή: {initial_rows}, Έγκυρα ζεύγη μετά καθαρισμό: {final_rows}")
        if coords_df.empty: return False, f"Δεν βρέθηκαν έγκυρα ζεύγη..."
        coordinates = list(coords_df.itertuples(index=False, name=None))
        if not coordinates: return False, "Η λίστα συντεταγμένων κενή..."
        center_lat = coords_df['latitude'].mean()
        center_lon = coords_df['longitude'].mean()
        center_location = [center_lat, center_lon]
        output_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Οι χάρτες θα αποθηκευτούν στον φάκελο: {output_dir}")

        # --- Υπολογισμός First-Last Απόστασης (ίδιος) ---
        first_last_distance_meters = 0; first_last_distance_str = "N/A"
        start_point_fl = coordinates[0] if coordinates else None
        end_point_fl = coordinates[-1] if len(coordinates) >=2 else start_point_fl
        if len(coordinates) >= 2:
            try: first_last_distance_meters = geodesic(start_point_fl, end_point_fl).meters; first_last_distance_str = f"{first_last_distance_meters:.2f} meters"; print(f"-> Απόσταση Πρώτου-Τελευταίου σημείου: {first_last_distance_str}")
            except Exception as e: first_last_distance_str = "Error"; print(f"Warn: {e}")
        # --- Υπολογισμός Μέγιστης Απόστασης ---
        print("Υπολογισμός μέγιστης απόστασης..."); max_distance_meters = 0.0; max_distance_points = (None, None)
        if len(coordinates) >= 2:
            for i in range(len(coordinates)):
                for j in range(i + 1, len(coordinates)):
                    point1 = coordinates[i]; point2 = coordinates[j]
                    try:
                        current_distance = geodesic(point1, point2).meters
                        # !!! ΔΙΟΡΘΩΣΗ ΣΥΝΤΑΞΗΣ: Σπάσιμο σε δύο γραμμές !!!
                        if current_distance > max_distance_meters:
                            max_distance_meters = current_distance
                            max_distance_points = (point1, point2)
                    except Exception as e: # Καλύτερα να πιάνουμε το exception για πιθανή εκτύπωση
                         # Απλά τυπώνουμε προειδοποίηση αν κάποιος υπολογισμός αποτύχει
                         # print(f"  -> Προειδοποίηση: Σφάλμα υπολ. απόστασης μεταξύ {point1} και {point2}: {e}")
                         pass # Αγνοούμε το σφάλμα και συνεχίζουμε
            print(f"-> Μέγιστη απόσταση που βρέθηκε: {max_distance_meters:.2f} meters")
            if max_distance_points[0]: print(f"   -> Μεταξύ: {max_distance_points[0]} και {max_distance_points[1]}")
        else: print("-> < 2 σημεία για μέγιστη απόσταση.")
        max_distance_str = f"{max_distance_meters:.2f} meters" if max_distance_points[0] else "N/A"

        # --- 1. Χάρτης με Circle Markers + Max Dist (ίδιος με πριν) ---
        print("Δημιουργία χάρτη Circle Markers + Max Dist...")
        map_circle_markers = folium.Map(location=center_location, zoom_start=16, tiles="OpenStreetMap")
        for lat, lon in coordinates: folium.CircleMarker(location=[lat, lon], radius=3, popup=f"({lat:.6f}, {lon:.6f})", color='lightblue', fill=True, fill_color='blue', fill_opacity=0.6).add_to(map_circle_markers)
        if max_distance_points[0]:
            p1, p2 = max_distance_points
            folium.Marker(location=p1, popup=f"Farthest 1\nMax Dist: {max_distance_str}", icon=folium.Icon(color='purple', icon='thumb-tack', prefix='fa')).add_to(map_circle_markers)
            folium.Marker(location=p2, popup=f"Farthest 2\nMax Dist: {max_distance_str}", icon=folium.Icon(color='purple', icon='thumb-tack', prefix='fa')).add_to(map_circle_markers)
            folium.PolyLine(locations=[p1, p2], color="purple", weight=2, dash_array='5, 5').add_to(map_circle_markers)
        circle_markers_filename = f"{output_prefix}_circle_markers_max_dist.html"
        circle_markers_path = os.path.join(output_dir, circle_markers_filename)
        map_circle_markers.save(circle_markers_path)
        print(f"-> Χάρτης Circle Markers + Max Dist αποθηκεύτηκε: {circle_markers_path}")

        # --- 2. Χάρτης με Polyline (ίδιος με πριν) ---
        print("Δημιουργία χάρτη Polyline...")
        map_polyline = folium.Map(location=center_location, zoom_start=16, tiles="CartoDB positron")
        folium.PolyLine(coordinates, color="red", weight=2.5, opacity=0.8).add_to(map_polyline)
        if start_point_fl: folium.Marker(start_point_fl, popup=f"Start\n({start_point_fl[0]:.6f}, {start_point_fl[1]:.6f})", icon=folium.Icon(color="green", icon="play")).add_to(map_polyline)
        if end_point_fl:
             end_popup_text = (f"End\n({end_point_fl[0]:.6f}, {end_point_fl[1]:.6f})\n"
                               f"First-Last Dist: {first_last_distance_str}\n"
                               f"Max Point Dist: {max_distance_str}")
             folium.Marker(end_point_fl, popup=end_popup_text, icon=folium.Icon(color="red", icon="stop")).add_to(map_polyline)
        polyline_filename = f"{output_prefix}_polyline.html"
        polyline_path = os.path.join(output_dir, polyline_filename)
        map_polyline.save(polyline_path)
        print(f"-> Χάρτης Polyline αποθηκεύτηκε: {polyline_path}")

        # --- 3. Χάρτης με Heatmap (ίδιος με πριν) ---
        print("Δημιουργία χάρτη Heatmap...")
        map_heatmap = folium.Map(location=center_location, zoom_start=16, tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri Satellite')
        heat_data = [[p[0], p[1]] for p in coordinates]
        gradient_rgba = {'0.2': 'rgba(0,0,255,0.2)', '0.4': 'rgba(0,255,255,0.3)', '0.6': 'rgba(0,255,0,0.5)', '0.8': 'rgba(255,255,0,0.7)', '1.0': 'rgba(255,0,0,0.8)'}
        if heat_data: HeatMap(heat_data, name='HeatMap', min_opacity=0.2, max_opacity=0.8, radius=18, blur=15, max_zoom=15, gradient=gradient_rgba).add_to(map_heatmap)
        heatmap_filename = f"{output_prefix}_heatmap.html"
        heatmap_path = os.path.join(output_dir, heatmap_filename)
        map_heatmap.save(heatmap_path)
        print(f"-> Χάρτης Heatmap αποθηκεύτηκε: {heatmap_path}")

        # --- 4. Χάρτης με Απλές Μπλε Κουκκίδες (ίδιος με πριν) ---
        print("Δημιουργία χάρτη Blue Dots (CircleMarkers)...")
        map_blue_dots = folium.Map(location=center_location, zoom_start=16, tiles="OpenStreetMap")
        for lat, lon in coordinates:
            folium.CircleMarker(location=[lat, lon], radius=3, popup=f"({lat:.6f}, {lon:.6f})", color='blue', fill=True, fill_color='blue', fill_opacity=0.7).add_to(map_blue_dots)
        blue_dots_filename = f"{output_prefix}_blue_dots.html"
        blue_dots_path = os.path.join(output_dir, blue_dots_filename)
        map_blue_dots.save(blue_dots_path)
        print(f"-> Χάρτης Blue Dots αποθηκεύτηκε: {blue_dots_path}")

        print("-" * 30)
        # (Το τελικό μήνυμα παραμένει ίδιο)
        final_message = (f"Οι χάρτες δημιουργήθηκαν επιτυχώς ({final_rows} έγκυρα σημεία).\n"
                         f"Απόσταση Πρώτου-Τελευταίου: {first_last_distance_str}\n"
                         f"Μέγιστη Απόσταση Σημείων: {max_distance_str}\n"
                         f"Αποθηκεύτηκαν ως:\n"
                         f"- {circle_markers_filename}\n"
                         f"- {polyline_filename}\n"
                         f"- {heatmap_filename}\n"
                         f"- {blue_dots_filename}\n"
                         f"στον φάκελο του script.")
        return True, final_message

    # (Τα blocks except παραμένουν ίδια)
    except FileNotFoundError: return False, f"Σφάλμα: Το αρχείο '{file_path}' δεν βρέθηκε."
    except pd.errors.EmptyDataError: return False, f"Σφάλμα: Το αρχείο '{os.path.basename(file_path)}' είναι κενό."
    except pd.errors.ParserError: return False, f"Σφάλμα: Δεν ήταν δυνατή η ανάλυση του αρχείου..."
    except ValueError as ve: return False, f"Σφάλμα τιμής: {ve}"
    except IndexError as ie: return False, f"Σφάλμα δείκτη στηλών: {ie}..."
    except Exception as e:
        import traceback
        print("--- UNEXPECTED ERROR ---"); print(traceback.format_exc()); print("------------------------")
        return False, f"Μη αναμενόμενο σφάλμα: {type(e).__name__} - {e}"

# --- Η κλάση PyQt6 MainWindow και το __main__ block παραμένουν ΑΚΡΙΒΩΣ ΙΔΙΑ με πριν ---
# ... (Ολόκληρη η κλάση MainWindow και το if __name__ == "__main__": ...)
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Folium Map Generator from CSV")
        self.setGeometry(100, 100, 500, 230)
        self.selected_file_path = ""

        # --- UI Elements ---
        self.file_label = QLabel("Αρχείο CSV Δεδομένων:")
        self.file_path_display = QLineEdit()
        self.file_path_display.setPlaceholderText("Επιλέξτε ένα αρχείο CSV...")
        self.file_path_display.setReadOnly(True)
        self.browse_button = QPushButton("Αναζήτηση...")
        self.browse_button.clicked.connect(self.browse_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_path_display)
        file_layout.addWidget(self.browse_button)

        self.lat_label = QLabel("Στήλη Latitude CSV (0-based):")
        self.lat_col_input = QLineEdit(DEFAULT_LAT_CSV_COL)
        lat_layout = QHBoxLayout()
        lat_layout.addWidget(self.lat_label)
        lat_layout.addWidget(self.lat_col_input)

        self.lon_label = QLabel("Στήλη Longitude CSV (0-based):")
        self.lon_col_input = QLineEdit(DEFAULT_LON_CSV_COL)
        lon_layout = QHBoxLayout()
        lon_layout.addWidget(self.lon_label)
        lon_layout.addWidget(self.lon_col_input)

        self.generate_button = QPushButton("Δημιουργία Χαρτών")
        self.generate_button.clicked.connect(self.generate_maps)
        self.generate_button.setStyleSheet("padding: 5px; font-weight: bold;")

        # --- Main Layout ---
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.file_label)
        main_layout.addLayout(file_layout)
        main_layout.addLayout(lat_layout)
        main_layout.addLayout(lon_layout)
        main_layout.addStretch(1)
        main_layout.addWidget(self.generate_button)
        self.setLayout(main_layout)

    def browse_file(self):
        """Opens a file dialog to select a CSV file."""
        fname, _ = QFileDialog.getOpenFileName(self, 'Επιλογή Αρχείου CSV', '', 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.selected_file_path = fname
            self.file_path_display.setText(fname)
            print(f"Selected file: {self.selected_file_path}")

    def generate_maps(self):
        """Gets inputs, validates them, calls processing function, and shows result."""
        file_path = self.selected_file_path
        lat_col_str = self.lat_col_input.text()
        lon_col_str = self.lon_col_input.text()

        if not file_path:
            QMessageBox.warning(self, "Ελλιπή Στοιχεία", "Παρακαλώ επιλέξτε πρώτα ένα αρχείο CSV.")
            return
        try:
            lat_col = int(lat_col_str)
            lon_col = int(lon_col_str)
            if lat_col < 0 or lon_col < 0:
                raise ValueError("Οι δείκτες στήλης πρέπει να είναι μη αρνητικοί.")
        except ValueError:
            QMessageBox.warning(self, "Λάθος Εισόδου", "Οι δείκτες στήλης Latitude και Longitude πρέπει να είναι έγκυροι ακέραιοι αριθμοί (π.χ., 0, 1, 3...).")
            return

        self.generate_button.setEnabled(False)
        self.generate_button.setText("Επεξεργασία...")
        QApplication.processEvents()

        success, message = process_and_create_maps(file_path, lat_col, lon_col)

        self.generate_button.setEnabled(True)
        self.generate_button.setText("Δημιουργία Χαρτών")

        if success:
            QMessageBox.information(self, "Ολοκλήρωση", message)
            try:
                output_dir = os.path.dirname(os.path.abspath(__file__))
                if sys.platform == 'win32':
                    os.startfile(output_dir)
                elif sys.platform == 'darwin':
                    os.system(f'open "{output_dir}"')
                else:
                    os.system(f'xdg-open "{output_dir}"')
            except Exception as e:
                print(f"Δεν ήταν δυνατό το αυτόματο άνοιγμα του φακέλου: {e}")
        else:
            QMessageBox.critical(self, "Σφάλμα", message)

# --- Main Execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())