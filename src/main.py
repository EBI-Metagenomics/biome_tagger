import argparse
import re
import xml.etree.ElementTree as ET
from tkinter import Tk, Listbox, END, StringVar, Entry, Button, TclError, Label, Frame, IntVar, Checkbutton, Scrollbar, \
    RIGHT, Text, Canvas, Y, SUNKEN, HORIZONTAL, LEFT, DISABLED, NORMAL
import tkinter.scrolledtext as tkscrolled

import logging
import webbrowser
import requests
from django.db.models import Q

from mgnify_backlog import mgnify_handler
from ena_portal_api import ena_handler

from biome_classifier import load_classifier

logging.basicConfig(level=logging.INFO, filename='biome_tagging.log')
logging.getLogger().addHandler(logging.StreamHandler())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', choices=['default', 'dev', 'prod'], default='prod')
    return parser.parse_args()


ENA_STUDY_FIELDS = 'secondary_study_accession,study_title,study_alias,description'


def get_biomes():
    biomes = mgnify_handler.Biome.objects.using('prod').all()
    return [d.lineage for d in biomes]


study_cache = {}


class Gui(Tk):
    biome_listbox = None
    biome_listbox_lbl = None
    biome_filter_var = None
    biome_filter_box = None

    biome_select_btn = None

    study_listbox = None
    study_listbox_lbl = None
    study_select_btn = None
    study_filter_var = None
    study_filter_box = None

    study_id_disp = None
    study_id_var = None

    study_title_disp = None
    study_title_var = None

    study_desc_disp = None
    study_desc_var = None

    study_scientific_names = None
    study_sci_names_var = None

    biome_selection_btn = None
    biome_selection = None
    biome_selection_lbl = None
    biome_tag_btn = None

    tagging_confirmation_lbl = None
    tagging_confirmation_var = None

    suggested_biomes = []

    ena_view_btn = None

    def __init__(self, biome_classifier=None):
        # Create the menu
        super().__init__()
        args = parse_args()
        self.btc = BiomeTaggingTool(args.db)
        self.biome_classifier = biome_classifier

        self.list_frame = Frame()
        self.list_frame.grid(row=1, column=0, padx=10, pady=3)
        self.details_frame = Frame()
        self.details_frame.grid(row=3, column=0, padx=10, pady=3)
        header = Label(self, text='Tagging biomes on db: ' + args.db)
        header.grid(row=0, column=0, padx=10, pady=3)

        self.title = 'Biome tagging!'

        self.biomes_list = get_biomes()


        self.init_biome_list()
        self.init_study_list()

        self.init_study_display()
        self.init_biome_conf_display()
        self.init_confirmation_line()

    def init_biome_list(self):
        self.biome_listbox_lbl = Label(self.list_frame, text='List of biomes (click to select)')
        self.biome_listbox_lbl.grid(row=0, column=1, padx=10, pady=3)
        self.biome_listbox = Listbox(self.list_frame, width=75)
        self.biome_listbox.grid(row=1, column=1, padx=10, pady=3)

        self.biome_listbox.bind('<Double-Button>', self.select_biome)
        for b in self.biomes_list:
            self.biome_listbox.insert(END, b)
        self.biome_filter_var = StringVar()
        self.biome_filter_var.trace("w", lambda name, index, mode: self.filter_biome_list())

        biome_filter_row = Frame(self.list_frame)
        biome_filter_row.grid(row=2, column=1, padx=10, pady=3)
        biome_filter_lbl = Label(biome_filter_row, text='Search biomes: ')
        biome_filter_lbl.grid(row=0, column=0, padx=10, pady=3)

        self.biome_match_case = IntVar()
        self.biome_filter_caps_checkbox = Checkbutton(biome_filter_row, text='Match case',
                                                      variable=self.biome_match_case, command=self.filter_biome_list)
        self.biome_filter_caps_checkbox.grid(row=1, column=0, padx=10, pady=3)

        self.biome_filter_box = Entry(biome_filter_row, textvariable=self.biome_filter_var, width=50)
        self.biome_select_btn = Button(biome_filter_row, text='Select biome', command=self.select_biome)
        self.biome_filter_box.grid(row=0, column=1, padx=10, pady=3)
        self.biome_select_btn.grid(row=0, column=2, padx=10, pady=3)

        self.filter_biome_list()


    def filter_study_list(self):
        search_term = self.study_filter_var.get()
        self.study_listbox.delete(0, END)
        list_studies = []


        # Append non-suggested biomes which pass filter
        for s in self.btc.studies:
            accessions = (s.primary_accession + ' ' + s.secondary_accession).lower()
            if search_term.lower() in accessions:
                list_studies.append(s.secondary_accession)

        # Insert into listbox and color items if needed
        for i, s in enumerate(list_studies):
            self.study_listbox.insert(END, s)

    def filter_biome_list(self):
        search_term = self.biome_filter_var.get()
        self.biome_listbox.delete(0, END)
        list_biomes = []

        index_colors = {}

        # Insert suggested biomes at top of list IF they match the filter text, and store indeces to colour them later
        for b in self.suggested_biomes:
            s = '{} ({} match)'.format(b[0], "{0:.2f}".format(b[1]))
            is_match = search_term.lower() in b[0].lower() if not self.biome_match_case.get() else search_term in b[0]
            if is_match:
                i = len(list_biomes)
                list_biomes.append(s)
                b_color = fmt_font_intensity(b[1])
                index_colors[i] = _from_rgb((255 - b_color, 0, b_color))

        # Append non-suggested biomes which pass filter
        for b in self.biomes_list:
            is_match = search_term.lower() in b.lower() if not self.biome_match_case.get() else search_term in b
            if is_match and b not in self.suggested_biomes:
                list_biomes.append(b)

        # Insert into listbox and color items if needed
        for i, b in enumerate(list_biomes):
            self.biome_listbox.insert(END, b)
            if i in index_colors:
                self.biome_listbox.itemconfig(i, {'fg': index_colors[i]})

    def init_study_list(self):
        self.study_listbox = Listbox(self.list_frame, width=75)
        self.update_study_list()
        self.study_listbox_lbl = Label(self.list_frame, text='List of studies that need tagging')
        self.study_listbox_lbl.grid(row=0, column=0, padx=10, pady=3)
        self.study_listbox.grid(row=1, column=0, padx=10, pady=3)


        study_filter_row = Frame(self.list_frame)
        study_filter_row.grid(row=2, column=0, padx=10, pady=3)
        study_filter_lbl = Label(study_filter_row, text='Search Study accession: ')
        study_filter_lbl.grid(row=0, column=0, padx=10, pady=3)

        self.study_filter_var = StringVar()
        self.study_filter_var.trace("w", lambda name, index, mode: self.filter_study_list())

        self.study_filter_box = Entry(study_filter_row, textvariable=self.study_filter_var, width=50)
        self.study_filter_box.grid(row=0, column=1, padx=10, pady=3)

        self.study_select_btn = Button(study_filter_row, text='Select study', command=self.select_study)
        self.study_listbox.bind('<Double-Button>', self.select_study)
        self.study_select_btn.grid(row=0, column=3, padx=10, pady=3)


        self.ena_view_btn = Button(self.list_frame, text='View study in ENA', command=self.view_in_ena)
        self.ena_view_btn.grid(row=3, column=0, padx=10, pady=3)

    def view_in_ena(self):
        webbrowser.open_new("https://www.ebi.ac.uk/ena/data/view/" + self.study_id_var.get().replace('Study id: ', ''))

    def init_study_display(self):
        self.study_id_var = StringVar(self)
        self.study_title_var = StringVar(self)
        self.study_desc_var = StringVar(self)
        self.study_sci_names_var = StringVar(self)

        self.study_id_disp = Label(self.details_frame, textvariable=self.study_id_var, wraplength=750)
        self.study_id_disp.grid(row=0, column=0, padx=10, pady=3)
        self.study_title_disp = Label(self.details_frame, textvariable=self.study_title_var, wraplength=750)
        self.study_title_disp.grid(row=1, column=0, padx=10, pady=3)

        self.study_desc_frame = Frame(self.details_frame)
        self.study_desc_frame.grid(row=2, column=0)

        self.study_desc_disp = tkscrolled.ScrolledText(self.study_desc_frame, height=20, width=140, wrap='word')
        self.study_desc_disp.insert(0.0, '\n' + self.study_desc_var.get())
        self.study_desc_disp['font'] = ('consolas', '14')
        self.study_desc_disp.pack(expand=True, fill='both')

        self.study_scientific_names = Label(self.details_frame, textvariable=self.study_sci_names_var, wraplength=750)
        self.study_scientific_names.grid(row=3, column=0, padx=10, pady=3)

    def fetch_study(self, study_id):
        if study_id not in study_cache:
            study = self.btc.studies.filter(secondary_accession=study_id)[0]
            d = self.btc.fetch_info(study)
            study_cache[study_id] = d
        else:
            d = study_cache[study_id]
        print('Fetched ' + study_id)
        return d

    def select_study(self, *args, **kwargs):
        try:
            print('selecting')
            study_id = self.study_listbox.get(self.study_listbox.curselection())
            d = self.fetch_study(study_id)
            self.study_id_var.set('Study id: {}'.format(study_id))
            self.study_title_var.set('Title: {}'.format(d['title']))
            text = 'Abstract: {}'.format(d['abstract'])
            self.study_desc_disp.delete(1.0, END)
            self.study_desc_disp.insert(1.0, '\n' + text)
            self.study_desc_disp.see(0.0)

            # self.study_sci_names_var.set('Environment variable names: {}'.format(", ".join(d['scientific_names'])))
            self.reset_confirmation_line()
            self.suggested_biomes = self.biome_classifier.pred_input((d['title'] or '') + ' ' + (d['abstract'] or ''))
            self.filter_biome_list()
        except TclError as e:
            logging.error(e)
            pass

    def reset_study_display(self):
        self.study_id_var.set('Study id:')
        self.study_title_var.set('Title:')
        self.study_desc_var.set('Description:')
        self.study_sci_names_var.set('Environment variable names:')

    def init_biome_conf_display(self):
        self.biome_selection = StringVar(value='Selected biome: ')
        self.biome_selection_lbl = Label(self.details_frame, textvariable=self.biome_selection)
        self.biome_selection_lbl.grid(row=0, column=1, padx=10, pady=3)
        self.biome_tag_btn = Button(self.details_frame, text='Tag biome', command=self.tag_biome_handler)
        self.biome_tag_btn.grid(row=1, column=1, padx=10, pady=3)

    def select_biome(self, *args, **kwargs):
        try:
            biome = self.biome_listbox.get(self.biome_listbox.curselection())
            self.biome_selection.set('Selected biome: {}'.format(biome))
            logging.info('Selected biome: ' + biome)
        except TclError:
            print('err')
            pass

    def tag_biome_handler(self, *args, **kwargs):
        study_id = self.study_id_var.get().replace('Study id: ', '')
        biome = self.biome_selection.get().replace('Selected biome: ', '')
        logging.info('Tagging {} with biome {}'.format(study_id, biome))
        lineage = re.sub('(\(\d\.\d+ match\))', '', biome)
        self.btc.tag_study(study_id, lineage)

        self.remove_study_from_list(study_id)
        self.reset_study_display()
        self.set_confirmation_line(study_id, biome)

        self.suggested_biomes = []
        self.filter_biome_list()

    def remove_study_from_list(self, study_id):
        logging.info('Removing study {} from list.'.format(study_id))
        self.btc.update_taggable_studies()
        self.update_study_list()

    def update_study_list(self):
        for i, s in enumerate(sorted([s.secondary_accession for s in self.btc.studies])):
            if self.study_listbox.get(i) != s:
                self.study_listbox.insert(i, s)
        self.study_listbox.delete(len(self.btc.studies), END)

    def init_confirmation_line(self):
        self.tagging_confirmation_var = StringVar(value='')
        self.tagging_confirmation_lbl = Label(self, textvariable=self.tagging_confirmation_var, fg="red")
        self.tagging_confirmation_lbl.grid(row=4, column=0, padx=10, pady=3)

    def set_confirmation_line(self, study_id, biome):
        s = 'Study {} was tagged with biome {}'.format(study_id, biome)
        self.tagging_confirmation_var.set(s)

    def reset_confirmation_line(self):
        self.tagging_confirmation_var.set('')


class BiomeTaggingTool:
    def __init__(self, db):
        self.db = db
        self.ena = ena_handler.EnaApiHandler()

        self.studies = []
        self.update_taggable_studies()

    def update_taggable_studies(self):
        self.studies = self.get_taggable_studies()

    def fetch_run_scientific_names(self, secondary_study_accession):
        vals = self.ena.get_study_runs(secondary_study_accession, fields='scientific_name')
        return set([v['scientific_name'] for v in vals])

    def fetch_info(self, study):
        s = self.ena.get_study(secondary_accession=study.secondary_accession)
        data = {
            'title': s.get('study_title') or s.get('title'),
            'abstract': s.get('study_description') or s.get('description')
        }
        return data

    def get_taggable_studies(self, study_accession=None):
        studies = mgnify_handler.Study.objects.using(self.db).filter(
            Q(run__biome_id__isnull=True) |
            Q(assembly__biome_id__isnull=True)).distinct()
        if study_accession:
            studies = studies.filter(Q(primary_accession=study_accession) | Q(secondary_accession=study_accession))
        return studies

    def tag_study(self, study_id, lineage):
        biome = mgnify_handler.Biome.objects.using(self.db).get(lineage=lineage)

        runs = mgnify_handler.Run.objects.using(self.db).filter(study__secondary_accession=study_id)
        assemblies = mgnify_handler.Assembly.objects.using(self.db).filter(study__secondary_accession=study_id)
        runs.update(biome=biome)
        assemblies.update(biome=biome)


max_intensity = 200
min_intensity = 100


def fmt_font_intensity(match_prob):
    val = ((max_intensity - min_intensity) * (match_prob)) + min_intensity
    return int(val)


def _from_rgb(rgb):
    """translates an rgb tuple of int to a tkinter friendly color code
    """
    return "#%02x%02x%02x" % rgb


def main():

    gui = Gui(biome_classifier=load_classifier.get_model())
    gui.mainloop()


if __name__ == '__main__':
    main()
