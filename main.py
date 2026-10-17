import os
import sqlite3
import urllib.parse
from datetime import date, timedelta
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

# Style Dark Luxe
Window.clearcolor = get_color_from_hex('#05070B')

DB_PATH = 'studiofit_mobile.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS membres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        telephone TEXT NOT NULL,
        genre TEXT NOT NULL,
        formule TEXT NOT NULL,
        date_fin TEXT NOT NULL,
        frais REAL DEFAULT 180.0,
        whatsapp_enabled INTEGER DEFAULT 1
    )''')
    conn.commit()
    conn.close()

init_db()

class StudioFitMobileApp(App):
    def build(self):
        self.title = "Studio Fit Pro"
        self.lang = "ar"  # Arabe par défaut
        
        main_layout = BoxLayout(orientation='vertical', padding=12, spacing=10)
        
        # Header Luxe
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=55, spacing=8)
        self.title_lbl = Label(
            text="[b][color=00F0FF]STUDIO FIT[/color][/b] [size=12]VIP[/size]", 
            markup=True, font_size=20, halign='left'
        )
        self.lang_btn = Button(
            text="🇫🇷 Français" if self.lang == "ar" else "🇲🇦 العربية", 
            size_hint_x=None, width=110,
            background_normal='', background_color=get_color_from_hex('#FFB703'),
            color=get_color_from_hex('#000000'), bold=True
        )
        self.lang_btn.bind(on_press=self.toggle_lang)
        
        header.add_widget(self.title_lbl)
        header.add_widget(self.lang_btn)
        main_layout.add_widget(header)
        
        # Barre d'actions & Recherche
        search_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=8)
        self.search_in = TextInput(
            hint_text="بحث بالاسم أو الهاتف..." if self.lang == "ar" else "Rechercher...",
            multiline=False, background_color=get_color_from_hex('#101726'),
            foreground_color=get_color_from_hex('#FFFFFF')
        )
        self.search_in.bind(text=self.filter_members)
        
        self.add_btn = Button(
            text="➕ مشترك جديد" if self.lang == "ar" else "➕ Nouveau", 
            size_hint_x=None, width=130,
            background_normal='', background_color=get_color_from_hex('#00F0FF'),
            color=get_color_from_hex('#000000'), bold=True
        )
        self.add_btn.bind(on_press=self.show_add_modal)
        
        search_box.add_widget(self.search_in)
        search_box.add_widget(self.add_btn)
        main_layout.add_widget(search_box)
        
        # Liste Scrollable des membres
        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.members_grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.members_grid.bind(minimum_height=self.members_grid.setter('height'))
        self.scroll.add_widget(self.members_grid)
        main_layout.add_widget(self.scroll)
        
        self.load_members()
        return main_layout

    def toggle_lang(self, instance):
        self.lang = "fr" if self.lang == "ar" else "ar"
        self.lang_btn.text = "🇫🇷 Français" if self.lang == "ar" else "🇲🇦 العربية"
        self.search_in.hint_text = "بحث بالاسم أو الهاتف..." if self.lang == "ar" else "Rechercher..."
        self.add_btn.text = "➕ مشترك جديد" if self.lang == "ar" else "➕ Nouveau"
        self.load_members()

    def filter_members(self, instance, text):
        self.load_members(query=text.strip())

    def load_members(self, query=None):
        self.members_grid.clear_widgets()
        conn = get_db()
        c = conn.cursor()
        if query:
            c.execute("SELECT * FROM membres WHERE nom LIKE ? OR prenom LIKE ? OR telephone LIKE ? ORDER BY id DESC",
                      (f"%{query}%", f"%{query}%", f"%{query}%"))
        else:
            c.execute("SELECT * FROM membres ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        today = date.today().isoformat()
        
        for r in rows:
            is_expired = r["date_fin"] < today
            card = BoxLayout(orientation='vertical', size_hint_y=None, height=90, padding=8, spacing=4)
            card.canvas.before.clear()
            
            # Nom + Statut
            top_line = BoxLayout(orientation='horizontal')
            name_text = f"{r['prenom']} {r['nom']} ({r['telephone']})"
            lbl_name = Label(text=name_text, font_size=14, bold=True, halign='left', text_size=(Window.width * 0.6, None))
            
            statut_txt = "🔴 منتهي" if is_expired else f"🟢 صالح ({r['date_fin']})"
            if self.lang == "fr":
                statut_txt = "🔴 Expiré" if is_expired else f"🟢 Actif ({r['date_fin']})"
            lbl_stat = Label(text=statut_txt, font_size=12, color=get_color_from_hex('#FF3366' if is_expired else '#00F5A0'))
            
            top_line.add_widget(lbl_name)
            top_line.add_widget(lbl_stat)
            card.add_widget(top_line)
            
            # Actions: WhatsApp + Prolonger
            bot_line = BoxLayout(orientation='horizontal', spacing=6)
            
            # WhatsApp button
            btn_wa = Button(
                text="💬 واتساب" if self.lang == "ar" else "💬 WhatsApp",
                background_normal='', background_color=get_color_from_hex('#25D366'),
                color=get_color_from_hex('#000000'), bold=True, size_hint_x=0.5
            )
            btn_wa.bind(on_press=lambda inst, m=r: self.open_whatsapp(m))
            
            # Renouveler button
            btn_renouv = Button(
                text="🔄 تمديد (+شهر)" if self.lang == "ar" else "🔄 Prolonger (+1M)",
                background_normal='', background_color=get_color_from_hex('#FFB703'),
                color=get_color_from_hex('#000000'), bold=True, size_hint_x=0.5
            )
            btn_renouv.bind(on_press=lambda inst, mid=r['id'], dfin=r['date_fin']: self.renew_member(mid, dfin))
            
            bot_line.add_widget(btn_wa)
            bot_line.add_widget(btn_renouv)
            card.add_widget(bot_line)
            
            self.members_grid.add_widget(card)

    def open_whatsapp(self, m):
        import webbrowser
        msg = f"Salam {m['prenom']}, l-abonnement dyalk f la salle STUDIO FIT ghadi ysali le {m['date_fin']}. Merci !"
        clean_tel = "".join(filter(str.isdigit, m['telephone']))
        encoded = urllib.parse.quote(msg)
        webbrowser.open(f"https://wa.me/{clean_tel}?text={encoded}")

    def renew_member(self, mid, current_fin):
        today = date.today()
        try:
            cur = date.fromisoformat(current_fin)
            new_date = cur + timedelta(days=30) if cur >= today else today + timedelta(days=30)
        except Exception:
            new_date = today + timedelta(days=30)
            
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE membres SET date_fin = ? WHERE id = ?", (new_date.isoformat(), mid))
        conn.commit()
        conn.close()
        self.load_members()

    def show_add_modal(self, instance):
        box = BoxLayout(orientation='vertical', padding=12, spacing=8)
        
        in_nom = TextInput(hint_text="النسب / Nom", multiline=False)
        in_prenom = TextInput(hint_text="الاسم / Prénom", multiline=False)
        in_tel = TextInput(hint_text="الهاتف / Tél (+212...)", multiline=False)
        
        box.add_widget(in_nom)
        box.add_widget(in_prenom)
        box.add_widget(in_tel)
        
        btn_save = Button(
            text="حفظ المشترك" if self.lang == "ar" else "Enregistrer",
            background_normal='', background_color=get_color_from_hex('#00F0FF'),
            color=get_color_from_hex('#000000'), bold=True, size_hint_y=None, height=45
        )
        
        popup = Popup(title="إضافة مشترك جديد" if self.lang == "ar" else "Nouveau Membre", content=box, size_hint=(0.85, 0.55))
        
        def save(inst):
            if in_nom.text and in_prenom.text and in_tel.text:
                fin = (date.today() + timedelta(days=30)).isoformat()
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO membres (nom, prenom, telephone, genre, formule, date_fin) VALUES (?, ?, ?, ?, ?, ?)",
                          (in_nom.text.strip(), in_prenom.text.strip(), in_tel.text.strip(), 'homme', 'Standard', fin))
                conn.commit()
                conn.close()
                popup.dismiss()
                self.load_members()
                
        btn_save.bind(on_press=save)
        box.add_widget(btn_save)
        popup.open()

if __name__ == '__main__':
    StudioFitMobileApp().run()
