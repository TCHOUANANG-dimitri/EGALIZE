"""Génère le rapport (rapport/Rapport_Projet2_Egaliseur_audio.docx) à partir des figures et des indicateurs.

    python scripts/generer_rapport.py

Le sommaire est un champ Word : il se met à jour à l'ouverture (ou clic droit > Mettre à jour).
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RACINE = Path(__file__).resolve().parents[1]
FIG = RACINE / "rapport" / "figures"
SORTIE = RACINE / "rapport" / "Rapport_Projet2_Egaliseur_audio.docx"
LOGOS = RACINE / "rapport" / "logos"
POLICE = "Times New Roman"
NOIR = RGBColor(0, 0, 0)
GRIS_TABLE = "D9D9D9"

doc = Document()
compteurs = {"figure": 0, "tableau": 0}


# ---------------------------------------------------------------------------
# Mise en forme générale
# ---------------------------------------------------------------------------
def police(style_ou_run, taille=None, gras=None, italique=None):
    font = style_ou_run.font
    font.name = POLICE
    if taille:
        font.size = Pt(taille)
    if gras is not None:
        font.bold = gras
    if italique is not None:
        font.italic = italique
    font.color.rgb = NOIR
    element = style_ou_run.element
    rpr = element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attribut in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attribut), POLICE)


section = doc.sections[0]
section.page_height, section.page_width = Cm(29.7), Cm(21.0)
section.top_margin = section.bottom_margin = Cm(2.5)
section.left_margin = section.right_margin = Cm(2.5)
section.different_first_page_header_footer = True

normal = doc.styles["Normal"]
police(normal, 12)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.15

for nom, taille, avant, apres in (("Heading 1", 15, 18, 10), ("Heading 2", 13, 12, 6), ("Heading 3", 12, 10, 4)):
    style = doc.styles[nom]
    police(style, taille, gras=True, italique=False)
    style.paragraph_format.space_before = Pt(avant)
    style.paragraph_format.space_after = Pt(apres)
    style.paragraph_format.keep_with_next = True

police(doc.styles["Caption"], 10, gras=False, italique=True)
doc.styles["Caption"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.styles["Caption"].paragraph_format.space_after = Pt(10)
police(doc.styles["List Bullet"], 12)
police(doc.styles["List Number"], 12)
for niveau in (1, 2):
    nom = f"TOC {niveau}"
    style = doc.styles[nom] if nom in [s.name for s in doc.styles] else doc.styles.add_style(nom, 1)
    police(style, 12, gras=(niveau == 1))
    style.paragraph_format.left_indent = Cm(0.6 * (niveau - 1))
    style.paragraph_format.space_after = Pt(1)
    style.paragraph_format.space_before = Pt(4 if niveau == 1 else 0)


# ---------------------------------------------------------------------------
# Petits outils d'écriture
# ---------------------------------------------------------------------------
def champ(paragraphe, instruction, texte=""):
    """Insère un champ Word (numéro de page, sommaire…)."""
    run = paragraphe.add_run()
    for type_, contenu in (("begin", None), ("instr", instruction), ("separate", None), ("text", texte), ("end", None)):
        if type_ == "instr":
            element = OxmlElement("w:instrText")
            element.set(qn("xml:space"), "preserve")
            element.text = contenu
            run._r.append(element)
        elif type_ == "text":
            element = OxmlElement("w:t")
            element.text = contenu
            run._r.append(element)
        else:
            element = OxmlElement("w:fldChar")
            element.set(qn("w:fldCharType"), type_)
            run._r.append(element)
    police(run)
    return run


def para(texte="", gras_debut=None, alignement=WD_ALIGN_PARAGRAPH.JUSTIFY, style=None, taille=None, italique=False):
    paragraphe = doc.add_paragraph(style=style)
    paragraphe.alignment = alignement
    if gras_debut:
        police(paragraphe.add_run(gras_debut), taille, gras=True)
    if texte:
        police(paragraphe.add_run(texte), taille, italique=italique)
    return paragraphe


def puces(elements, style="List Bullet"):
    for element in elements:
        p = doc.add_paragraph(style=style)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(3)
        if isinstance(element, tuple):
            police(p.add_run(element[0]), gras=True)
            police(p.add_run(element[1]))
        else:
            police(p.add_run(element))


def equation(texte):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    police(p.add_run(texte), italique=True)


def titre(texte, niveau=1):
    h = doc.add_heading(texte, level=niveau)
    for run in h.runs:
        police(run)
    return h


def legende(type_, texte):
    compteurs[type_] += 1
    p = doc.add_paragraph(style="Caption")
    prefixe = "Figure" if type_ == "figure" else "Tableau"
    police(p.add_run(f"{prefixe} {compteurs[type_]} : "), 10, gras=False, italique=False)
    police(p.add_run(texte), 10, italique=True)
    if type_ == "tableau":
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_after = Pt(4)
    return compteurs[type_]


def figure(nom, texte, largeur=15.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(FIG / f"{nom}.png"), width=Cm(largeur))
    return legende("figure", texte)


def sans_bordures(table):
    tbl_pr = table._tbl.tblPr
    bordures = OxmlElement("w:tblBorders")
    for cote in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{cote}")
        element.set(qn("w:val"), "nil")
        bordures.append(element)
    tbl_pr.append(bordures)


def figures_cote_a_cote(gauche, droite, texte, largeur=7.8):
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sans_bordures(table)
    for cellule, (nom, lettre) in zip(table.rows[0].cells, ((gauche, "a"), (droite, "b"))):
        cellule.width = Cm(8.0)
        p = cellule.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(FIG / f"{nom}.png"), width=Cm(largeur))
        sous = cellule.add_paragraph()
        sous.alignment = WD_ALIGN_PARAGRAPH.CENTER
        police(sous.add_run(f"({lettre})"), 10)
    lignes_solidaires(table, avec_suivant=True)
    return legende("figure", texte)


def lignes_solidaires(table, avec_suivant=True):
    """Empêche les lignes du tableau de se couper et les garde sur la même page."""
    for index, ligne in enumerate(table.rows):
        tr_pr = ligne._tr.get_or_add_trPr()
        insecable = OxmlElement("w:cantSplit")
        tr_pr.append(insecable)
        derniere = index == len(table.rows) - 1
        for cellule in ligne.cells:
            for paragraphe in cellule.paragraphs:
                paragraphe.paragraph_format.keep_with_next = avec_suivant or not derniere


def ombrer(cellule, couleur):
    tc_pr = cellule._tc.get_or_add_tcPr()
    ombre = OxmlElement("w:shd")
    ombre.set(qn("w:val"), "clear")
    ombre.set(qn("w:color"), "auto")
    ombre.set(qn("w:fill"), couleur)
    tc_pr.append(ombre)


def tableau(entetes, lignes, largeurs, texte, taille=10):
    legende("tableau", texte)
    table = doc.add_table(rows=1 + len(lignes), cols=len(entetes))
    table.style = doc.styles["Table Grid"]
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, ligne in enumerate([entetes, *lignes]):
        for j, valeur in enumerate(ligne):
            cellule = table.rows[i].cells[j]
            cellule.width = Cm(largeurs[j])
            p = cellule.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            police(p.add_run(str(valeur)), taille, gras=(i == 0))
            if i == 0:
                ombrer(cellule, GRIS_TABLE)
    lignes_solidaires(table, avec_suivant=False)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return compteurs["tableau"]


def lien(paragraphe, url):
    """Lien hypertexte cliquable, centré, souligné."""
    paragraphe.alignment = WD_ALIGN_PARAGRAPH.CENTER
    identifiant = paragraphe.part.relate_to(
        url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlien = OxmlElement("w:hyperlink")
    hyperlien.set(qn("r:id"), identifiant)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    polices = OxmlElement("w:rFonts")
    for attribut in ("w:ascii", "w:hAnsi", "w:cs"):
        polices.set(qn(attribut), POLICE)
    couleur = OxmlElement("w:color")
    couleur.set(qn("w:val"), "1F3A93")
    souligne = OxmlElement("w:u")
    souligne.set(qn("w:val"), "single")
    for element in (polices, couleur, souligne):
        rpr.append(element)
    run.append(rpr)
    texte = OxmlElement("w:t")
    texte.text = url
    run.append(texte)
    hyperlien.append(run)
    paragraphe._p.append(hyperlien)


def saut_de_page():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------------------
# En-tête et pied de page (absents de la page de garde)
# ---------------------------------------------------------------------------
entete = section.header.paragraphs[0]
entete.alignment = WD_ALIGN_PARAGRAPH.RIGHT
police(entete.add_run("Projet 2 : conception d'un égaliseur audio numérique"), 9, italique=True)
bordure = OxmlElement("w:pBdr")
bas = OxmlElement("w:bottom")
for attribut, valeur in (("w:val", "single"), ("w:sz", "4"), ("w:space", "4"), ("w:color", "808080")):
    bas.set(qn(attribut), valeur)
bordure.append(bas)
entete._p.get_or_add_pPr().append(bordure)

pied = section.footer.paragraphs[0]
pied.alignment = WD_ALIGN_PARAGRAPH.CENTER
champ(pied, "PAGE", "1")


# ---------------------------------------------------------------------------
# Page de garde
# ---------------------------------------------------------------------------
def ligne_garde(texte, taille, gras=False, italique=False, avant=0, apres=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(avant)
    p.paragraph_format.space_after = Pt(apres)
    police(p.add_run(texte), taille, gras=gras, italique=italique)
    return p


# Logos des deux établissements, en haut à gauche et à droite
entete_garde = doc.add_table(rows=1, cols=2)
entete_garde.alignment = WD_TABLE_ALIGNMENT.CENTER
sans_bordures(entete_garde)
for cellule, (fichier, nom) in zip(entete_garde.rows[0].cells, (
        ("logo_universite_douala.png", ("UNIVERSITÉ DE DOUALA", "THE UNIVERSITY OF DOUALA")),
        ("logo_polytechnique_douala.png", ("ÉCOLE NATIONALE SUPÉRIEURE", "POLYTECHNIQUE DE DOUALA")))):
    cellule.width = Cm(8.0)
    p_logo = cellule.paragraphs[0]
    p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_logo.add_run().add_picture(str(LOGOS / fichier), height=Cm(3.0))
    for ligne in nom:
        p_nom = cellule.add_paragraph()
        p_nom.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_nom.paragraph_format.space_after = Pt(0)
        police(p_nom.add_run(ligne), 10, gras=True)

ligne_garde("Filière : Science des données et Intelligence Artificielle (SDIA 4)", 12, avant=24)
ligne_garde("Module : Traitement du signal", 12, avant=30)
ligne_garde("Projet de fin de module", 12, italique=True)

trait = ligne_garde("", 6, avant=30)
pbdr = OxmlElement("w:pBdr")
haut = OxmlElement("w:top")
for attribut, valeur in (("w:val", "single"), ("w:sz", "8"), ("w:space", "1"), ("w:color", "000000")):
    haut.set(qn(attribut), valeur)
pbdr.append(haut)
trait._p.get_or_add_pPr().append(pbdr)

ligne_garde("PROJET 2", 14, gras=True, avant=6, apres=8)
ligne_garde("CONCEPTION D'UN ÉGALISEUR", 22, gras=True)
ligne_garde("AUDIO NUMÉRIQUE", 22, gras=True, apres=6)

trait2 = ligne_garde("", 6, apres=24)
pbdr2 = OxmlElement("w:pBdr")
bas2 = OxmlElement("w:bottom")
for attribut, valeur in (("w:val", "single"), ("w:sz", "8"), ("w:space", "1"), ("w:color", "000000")):
    bas2.set(qn(attribut), valeur)
pbdr2.append(bas2)
trait2._p.get_or_add_pPr().append(pbdr2)

ligne_garde("Réalisé par :", 12, gras=True, avant=18, apres=4)
for membre in ("TCHOUANANG GHEMDJOK PASCAL DIMITRI", "HALIMATOU SADIYA", "NGETCHOU IVANA ELFRID"):
    ligne_garde(membre, 12)
ligne_garde("Sous l'encadrement de :", 12, gras=True, avant=18, apres=4)
ligne_garde("MPOH LOBE HENRY PASCAL WILL", 12)
ligne_garde("Année académique 2026-2027", 12, avant=40)
ligne_garde("Date de remise : 27 novembre 2026", 12)
saut_de_page()

# ---------------------------------------------------------------------------
# Sommaire
# ---------------------------------------------------------------------------
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(18)
police(p.add_run("SOMMAIRE"), 15, gras=True)
champ(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u', "Clic droit puis « Mettre à jour les champs » pour afficher le sommaire.")
saut_de_page()

# ---------------------------------------------------------------------------
# 1. Introduction
# ---------------------------------------------------------------------------
titre("1. Introduction")
titre("1.1 Contexte", 2)
para("Un égaliseur est un outil qui modifie séparément le niveau de différentes plages de fréquences d'un "
     "signal audio. Il est présent dans la plupart des chaînes de reproduction sonore, des lecteurs de "
     "musique aux consoles de mixage, et permet par exemple de renforcer les basses d'un morceau ou de "
     "rendre une voix plus intelligible. Sa réalisation repose sur des notions centrales du traitement "
     "numérique du signal : l'échantillonnage, l'analyse spectrale et le filtrage.")
titre("1.2 Problématique", 2)
para("Comment séparer un signal audio numérique en trois bandes de fréquences (graves, médiums, aigus), "
     "modifier le niveau de chacune d'elles, puis les recombiner sans altérer le signal lorsque aucun gain "
     "n'est appliqué, et sans provoquer d'écrêtage lorsque des gains sont appliqués ?")
titre("1.3 Objectifs", 2)
puces([
    "importer un fichier audio de 10 à 30 secondes sans modifier l'original, et relever ses caractéristiques ;",
    "visualiser le signal dans le domaine temporel et dans le domaine fréquentiel ;",
    "concevoir les filtres qui séparent le signal en trois bandes et justifier leurs paramètres ;",
    "appliquer un gain à chaque bande, recombiner les bandes et écouter le résultat ;",
    "produire au moins deux versions égalisées et comparer leurs spectres à celui de l'original ;",
    "surveiller l'écrêtage numérique et signaler toute modification du niveau global.",
])

# ---------------------------------------------------------------------------
# 2. Matériel et méthode
# ---------------------------------------------------------------------------
titre("2. Matériel et méthode")
titre("2.1 Matériel et logiciels", 2)
para("Le projet est entièrement réalisé sur ordinateur, sans dispositif d'acquisition. Les outils utilisés sont :")
puces([
    ("Langage : ", "Python 3.10."),
    ("Bibliothèques : ", "NumPy (calcul numérique), SciPy (lecture et écriture des fichiers WAV, estimation du "
                         "spectre, récurrence des filtres), Plotly et Matplotlib (graphiques)."),
    ("Interface : ", "application web développée avec Streamlit, exécutée localement dans un navigateur."),
    ("Écoute : ", "casque audio relié à l'ordinateur."),
])
titre("2.2 Source des données", 2)
para("Le signal étudié est un extrait du fichier « Techno music 001.wav », un morceau de musique "
     "électronique publié sur Wikimedia Commons par Luisalvaz le 9 mars 2024, sous licence CC0 (domaine "
     "public) :")
lien(doc.add_paragraph(), "https://commons.wikimedia.org/wiki/File:Techno_music_001.wav")
para("Le fichier utilisé est identique à celui publié (même taille, 63 030 086 octets, et même durée, "
     "238,21 s). Il est conservé sans modification dans le dossier des données brutes. L'extrait et les "
     "versions égalisées sont enregistrés dans des fichiers distincts.")
titre("2.3 Protocole", 2)
puces([
    "Lecture du fichier original et relevé de ses caractéristiques (format, fréquence d'échantillonnage, nombre de canaux, durée).",
    "Extraction des 20 premières secondes dans un nouveau fichier, sans conversion des échantillons.",
    "Calcul et affichage du spectre de l'extrait.",
    "Séparation de l'extrait en trois bandes à l'aide de filtres passe-bas, avec des fréquences de coupure de 250 Hz et 4 kHz.",
    "Application des gains de chaque version, recombinaison des bandes et contrôle de la crête du signal obtenu.",
    "Export des versions égalisées au format WAV, comparaison des spectres et des indicateurs avant et après traitement, écoute.",
], style="List Number")
para("La figure 1 résume la chaîne de traitement mise en œuvre.")
figure("fig00_chaine", "Chaîne de traitement de l'égaliseur trois bandes.")
titre("2.4 Application développée", 2)
para("Le traitement est accessible dans l'application développée pour le projet, organisée en trois pages : « Fichier » "
     "(import, choix de l'extrait, spectre), « Bandes » (écoute et réglage du gain de chaque bande) et "
     "« Recombinaison » (comparaison avec l'original, écoute et export). Les figures présentées dans ce "
     "rapport sont des captures de cette application. Les versions égalisées remises sont produites par le "
     "script scripts/generer_versions.py, qui utilise exactement les mêmes filtres que l'application.")
para("L'application est publiée en ligne et utilisable depuis un navigateur, sans installation, à l'adresse :")
lien(doc.add_paragraph(), "https://egalize.streamlit.app/")

# ---------------------------------------------------------------------------
# 3. Description des données
# ---------------------------------------------------------------------------
titre("3. Description des données")
titre("3.1 Caractéristiques du signal", 2)
tableau(
    ["Caractéristique", "Valeur"],
    [
        ["Grandeur mesurée", "Pression acoustique numérisée (amplitude normalisée, sans unité)"],
        ["Format", "WAV, PCM entier 32 bits"],
        ["Fréquence d'échantillonnage", "44 100 Hz"],
        ["Nombre de canaux", "2 (stéréo)"],
        ["Durée du fichier original", "238,21 s (10 505 007 échantillons par canal)"],
        ["Extrait étudié", "de 0 à 20 s, soit 882 000 échantillons par canal"],
        ["Fréquence de Nyquist", "22 050 Hz"],
        ["Crête de l'extrait", "−4,94 dBFS"],
        ["Valeur efficace de l'extrait", "−21,61 dBFS"],
    ],
    [5.5, 10.5],
    "Caractéristiques du fichier et de l'extrait étudié.",
)
para("Les amplitudes sont exprimées en valeur normalisée : la pleine échelle numérique correspond à ±1, "
     "soit 0 dBFS (décibels relatifs à la pleine échelle). L'en-tête du fichier original annonce quelques "
     "octets de plus que les données réellement présentes ; les échantillons lisibles sont utilisés "
     "normalement et l'extrait de 20 secondes n'est pas concerné.")
titre("3.2 Visualisation du signal brut", 2)
para("Le spectre est estimé par la méthode de Welch : moyenne des transformées de Fourier de segments de "
     "8 192 échantillons, soit une résolution d'environ 5,4 Hz. L'axe des fréquences est logarithmique, ce "
     "qui donne la même largeur à chaque octave.")
figure("fig01_spectre_original", "Spectre de l'extrait original. Les zones colorées et les traits pointillés "
       "indiquent les trois bandes et les fréquences de coupure (250 Hz et 4 kHz).", 13.5)
figure("fig03_recombine_0dB_onde", "Forme d'onde de l'extrait sur 20 s (enveloppe des valeurs minimales et "
       "maximales). La courbe grise est l'original ; la courbe bleue, confondue avec elle, est le signal "
       "recombiné avec des gains nuls.", 11)
titre("3.3 Caractéristiques importantes", 2)
para("Le spectre montre que l'énergie de l'extrait est fortement concentrée dans les basses fréquences, avec "
     "des pics marqués entre 60 et 80 Hz (grosse caisse et ligne de basse). Le niveau décroît ensuite de "
     "façon régulière vers les aigus et chute nettement au-delà de 15 kHz. La répartition de la puissance "
     "dans les trois zones est donnée dans le tableau 2. Le signal est un enregistrement musical propre : on "
     "n'y observe pas de bruit de fond ni de perturbation particulière. La forme d'onde reste sous la pleine "
     "échelle, avec une marge de 4,94 dB avant l'écrêtage.")
tableau(
    ["Zone", "Plage de fréquences", "Part de la puissance"],
    [["Graves", "0 à 250 Hz", "88,4 %"], ["Médiums", "250 Hz à 4 kHz", "8,2 %"], ["Aigus", "4 kHz à 22,05 kHz", "3,4 %"]],
    [4.0, 6.0, 5.0],
    "Répartition de la puissance de l'extrait original dans les trois zones.",
)

# ---------------------------------------------------------------------------
# 4. Méthodes de traitement
# ---------------------------------------------------------------------------
titre("4. Méthodes de traitement")
titre("4.1 Principe de l'égaliseur", 2)
para("L'égaliseur suit trois étapes : le signal x est séparé en trois bandes (graves, médiums, aigus), "
     "chaque bande est multipliée par un facteur qui correspond au gain choisi, puis les trois bandes sont "
     "additionnées. Les trois bandes sont construites à partir d'un seul type de filtre, le passe-bas.")
titre("4.2 Filtre passe-bas par lissage exponentiel", 2)
para("Le filtre de base est le lissage exponentiel, version numérique du circuit RC (passe-bas d'ordre 1). "
     "À chaque échantillon, la sortie y rattrape une fraction α de son écart avec l'entrée x :")
equation("y[n] = y[n−1] + α · ( x[n] − y[n−1] ),    avec    α = 1 − exp(−2π · f₀ / fₛ)")
para("Plus α est petit, plus la sortie évolue lentement et plus la fréquence de coupure est basse. Ce filtre "
     "est récursif : il ne garde en mémoire que la sortie précédente, ce qui le rend très économique.")
titre("4.3 Filtrage aller-retour", 2)
para("Appliqué une seule fois, le lissage retarde le signal (déphasage), et ce retard dépend de la fréquence. "
     "Comme l'égaliseur traite un fichier complet, le filtre est appliqué deux fois : une fois dans le sens "
     "du temps, puis une fois sur le signal retourné. Les retards des deux passages se compensent et le "
     "déphasage est nul. L'atténuation est en revanche appliquée deux fois : pour conserver −3 dB "
     "exactement à la fréquence de coupure fc, le filtre est réglé à une fréquence légèrement plus élevée :")
equation("f₀ = fc / √(√2 − 1) ≈ 1,554 · fc")
para("Le tableau 3 donne le gain mesuré du passe-bas obtenu pour fc = 250 Hz. La pente vaut environ "
     "−9 dB par octave entre 500 Hz et 1 kHz et tend vers −12 dB par octave plus loin de la coupure.")
tableau(
    ["Fréquence", "125 Hz", "250 Hz", "500 Hz", "1 000 Hz"],
    [["Gain mesuré", "−0,9 dB", "−3,0 dB", "−8,5 dB", "−17,6 dB"]],
    [3.4, 3.0, 3.0, 3.0, 3.0],
    "Gain du passe-bas aller-retour réglé à 250 Hz, mesuré sur des sinusoïdes pures.",
)
titre("4.4 Construction des trois bandes", 2)
para("Les trois bandes sont obtenues avec deux passe-bas, notés PB, réglés aux deux fréquences de coupure :")
equation("graves = PB₂₅₀(x)        médiums = PB₄₀₀₀(x) − PB₂₅₀(x)        aigus = x − PB₄₀₀₀(x)")
para("La bande des aigus est donc un passe-haut (le signal privé de ce que garde le passe-bas) et la bande "
     "des médiums un passe-bande (différence de deux passe-bas). En additionnant les trois expressions, on "
     "retrouve exactement x : avec des gains nuls, l'égaliseur ne modifie pas le signal. Cette propriété a "
     "été vérifiée sur l'extrait : l'écart maximal entre le signal recombiné et l'original vaut 5,6 × 10⁻¹⁷, "
     "c'est-à-dire la précision de calcul de l'ordinateur.")
titre("4.5 Choix des fréquences de coupure", 2)
puces([
    ("250 Hz : ", "sépare les fondamentales graves (grosse caisse, basse, généralement sous 200 Hz) du reste du "
                  "contenu musical."),
    ("4 kHz : ", "sépare la zone de la voix et de la plupart des instruments (250 Hz à 4 kHz) de la brillance "
                 "(cymbales, sifflantes, harmoniques élevées)."),
    ("Normalisation : ", "les deux valeurs appartiennent à la série normalisée des fréquences par tiers "
                         "d'octave (ISO 266) et sont largement inférieures à la fréquence de Nyquist (22 050 Hz)."),
])
titre("4.6 Application des gains", 2)
para("Un gain G exprimé en décibels correspond à un facteur multiplicatif d'amplitude :")
equation("facteur = 10^(G / 20)")
para("Ainsi, +6 dB multiplie l'amplitude par 2 et −6 dB la divise par 2. L'application autorise des gains "
     "de −12 à +12 dB par pas de 1 dB.")
titre("4.7 Contrôle de l'écrêtage", 2)
para("Un échantillon numérique ne peut pas dépasser la pleine échelle (±1). Après recombinaison, la crête du "
     "signal est mesurée. Si elle dépasse 0 dBFS, le signal entier est multiplié par un facteur qui ramène "
     "sa crête à −1 dBFS. Cet abaissement de niveau est indiqué dans l'application et reporté dans les "
     "résultats. Aucune autre normalisation n'est appliquée : l'écoute et l'export se font au niveau réel.")

# ---------------------------------------------------------------------------
# 5. Résultats
# ---------------------------------------------------------------------------
titre("5. Résultats")
titre("5.1 Versions étudiées", 2)
tableau(
    ["Version", "Graves", "Médiums", "Aigus", "Intention"],
    [
        ["Version 1", "+6 dB", "0 dB", "−1 dB", "Renforcer les basses"],
        ["Version 2", "0 dB", "+8 dB", "+2 dB", "Mettre en avant les médiums"],
        ["Version 3", "+2 dB", "−1 dB", "+10 dB", "Accentuer la brillance"],
    ],
    [2.6, 2.2, 2.2, 2.2, 6.8],
    "Gains appliqués aux trois bandes pour chaque version (coupures : 250 Hz et 4 kHz).",
)
titre("5.2 Séparation en trois bandes", 2)
para("La figure 4 montre le spectre de chaque bande obtenue avant application des gains. Chaque bande "
     "domine dans sa zone, mais les transitions sont progressives : chaque bande conserve une partie de "
     "l'énergie des zones voisines.")
figure("fig02_trois_bandes", "Spectres des trois bandes séparées, avant application des gains.", 14)
titre("5.3 Vérification de la reconstruction", 2)
para("Avec des gains nuls, le spectre du signal recombiné se superpose exactement à celui de l'original "
     "(figure 5), comme la forme d'onde présentée à la figure 3.")
figure("fig03_recombine_0dB_spectre", "Spectre de l'original et du signal recombiné avec des gains nuls : "
       "les deux courbes sont confondues.", 11)

versions = [
    (1, "graves", "Version 1 : renforcement des graves",
     "La bande des graves est amplifiée de 6 dB et celle des aigus atténuée de 1 dB. Le spectre recombiné "
     "s'élève nettement sous 250 Hz, reste proche de l'original dans les médiums et baisse légèrement dans "
     "les aigus. La crête atteint −2,76 dBFS : aucun abaissement de niveau n'est nécessaire.",
     "Bande des graves, version 1 : (a) spectre avant et après le gain de +6 dB ; (b) forme d'onde avant et après le gain.",
     "Version 1 comparée à l'original : (a) spectres ; (b) formes d'onde."),
    (2, "mediums", "Version 2 : mise en avant des médiums",
     "La bande des médiums est amplifiée de 8 dB et celle des aigus de 2 dB. La crête du signal recombiné "
     "atteint +1,27 dBFS et dépasserait donc la pleine échelle : le niveau de l'ensemble du signal a été "
     "abaissé de 2,27 dB pour ramener la crête à −1 dBFS. Les spectres de la figure 9 sont ceux du signal "
     "recombiné avant cet abaissement.",
     "Bande des médiums, version 2 : (a) spectre avant et après le gain de +8 dB ; (b) forme d'onde avant et après le gain.",
     "Version 2 comparée à l'original, avant l'abaissement de niveau de 2,27 dB : (a) spectres ; (b) formes d'onde."),
    (3, "aigus", "Version 3 : accentuation des aigus",
     "La bande des aigus est amplifiée de 10 dB, celle des graves de 2 dB et celle des médiums atténuée de "
     "1 dB. Le spectre recombiné s'élève au-delà de 4 kHz. La crête atteint −2,04 dBFS : aucun abaissement "
     "de niveau n'est nécessaire.",
     "Bande des aigus, version 3 : (a) spectre avant et après le gain de +10 dB ; (b) forme d'onde avant et après le gain.",
     "Version 3 comparée à l'original : (a) spectres ; (b) formes d'onde."),
]
for numero, bande, intitule, texte, legende_bande, legende_recombine in versions:
    titre(f"5.{numero + 3} {intitule}", 2)
    para(texte)
    figures_cote_a_cote(f"v{numero}_{bande}_spectre", f"v{numero}_{bande}_onde", legende_bande)
    figures_cote_a_cote(f"v{numero}_recombine_spectre", f"v{numero}_recombine_onde", legende_recombine)

titre("5.7 Indicateurs avant et après traitement", 2)
para("Pour chaque version, la variation de niveau de chaque zone est mesurée sur le spectre : c'est le "
     "rapport, en décibels, entre la puissance de la zone après traitement et sa puissance dans l'original. "
     "Les valeurs portent sur les fichiers exportés, donc après l'éventuel abaissement de niveau.")
tableau(
    ["Version", "Gains demandés G / M / A (dB)", "Variations mesurées G / M / A (dB)", "Crête avant correction",
     "Abaissement", "Valeur efficace"],
    [
        ["Original", "—", "—", "−4,94 dBFS", "—", "−21,61 dBFS"],
        ["Version 1", "+6 / 0 / −1", "+5,8 / +1,5 / −0,5", "−2,76 dBFS", "0 dB", "−16,16 dBFS"],
        ["Version 2", "0 / +8 / +2", "−1,7 / +4,5 / +3,1", "+1,27 dBFS", "−2,27 dB", "−22,08 dBFS"],
        ["Version 3", "+2 / −1 / +10", "+1,9 / +0,9 / +6,6", "−2,04 dBFS", "0 dB", "−19,52 dBFS"],
    ],
    [2.2, 3.2, 3.4, 2.5, 2.2, 2.5],
    "Gains demandés et variations mesurées par zone (G : graves, M : médiums, A : aigus), niveaux de crête et valeur efficace.",
    taille=9.5,
)
tableau(
    ["Version", "Graves", "Médiums", "Aigus"],
    [["Original", "88,4 %", "8,2 %", "3,4 %"], ["Version 1", "95,8 %", "3,3 %", "0,9 %"],
     ["Version 2", "66,8 %", "25,5 %", "7,7 %"], ["Version 3", "84,3 %", "6,1 %", "9,6 %"]],
    [4.0, 3.5, 3.5, 3.5],
    "Répartition de la puissance dans les trois zones, avant et après traitement.",
)

# ---------------------------------------------------------------------------
# 6. Discussion
# ---------------------------------------------------------------------------
titre("6. Discussion")
titre("6.1 Interprétation des résultats", 2)
para("Les trois versions modifient le spectre dans le sens demandé, et la reconstruction est exacte lorsque "
     "les gains sont nuls. Les variations mesurées ne sont toutefois pas égales aux gains demandés :")
puces([
    ("Version 1 : ", "les graves gagnent 5,8 dB pour 6 dB demandés, car leur énergie est concentrée entre 60 et "
                     "80 Hz, loin de la coupure. Les médiums gagnent 1,5 dB alors qu'aucun gain n'était demandé : "
                     "la partie basse des médiums (250 à 500 Hz) appartient encore en partie à la bande des graves "
                     "et reçoit donc une part du gain de +6 dB."),
    ("Version 2 : ", "avant l'abaissement de niveau, les médiums gagnent environ 6,7 dB pour 8 dB demandés et les "
                     "aigus environ 5,3 dB pour 2 dB demandés. Le fort gain des médiums déborde sur le début de la "
                     "zone des aigus (4 à 8 kHz). L'abaissement de 2,27 dB, appliqué à tout le signal, explique "
                     "ensuite la variation négative des graves (−1,7 dB)."),
    ("Version 3 : ", "les aigus ne gagnent que 6,6 dB pour 10 dB demandés. L'énergie de la zone des aigus se situe "
                     "surtout entre 4 et 8 kHz, juste au-dessus de la coupure, là où la bande des aigus ne contient "
                     "qu'une partie du signal. À l'inverse, les médiums augmentent de 0,9 dB malgré la consigne de "
                     "−1 dB, à cause du débordement du gain de +10 dB sous 4 kHz."),
])
para("Ces écarts ont une cause commune : les filtres utilisés ont des pentes douces (environ −12 dB par octave "
     "au mieux). Les bandes se chevauchent autour des fréquences de coupure, et chaque fréquence reçoit un "
     "mélange des gains de sa bande et de ses voisines.")
titre("6.2 Difficultés rencontrées", 2)
puces([
    "Le lecteur audio de l'interface normalisait automatiquement les signaux, ce qui masquait les différences de "
    "niveau entre les versions. Les signaux lui sont désormais transmis au niveau réel.",
    "Le réglage des filtres obtenus par soustraction ne correspond pas directement à la formule du passe-bas : "
    "la fréquence de réglage a dû être corrigée pour conserver −3 dB à la coupure.",
    "Un gain important peut faire dépasser la pleine échelle, comme pour la version 2, et impose un contrôle de crête.",
])
titre("6.3 Limites", 2)
puces([
    "Les pentes des filtres sont douces : la séparation des bandes est imparfaite et les gains obtenus s'écartent des gains demandés.",
    "Le filtrage aller-retour exige de disposer du signal complet : il convient au traitement d'un fichier, pas à un traitement en temps réel.",
    "L'étude porte sur un seul extrait d'un seul genre musical, dont l'énergie est concentrée dans les graves.",
    "L'abaissement de niveau qui évite l'écrêtage modifie le volume global de la version concernée.",
    "Les indicateurs sont des mesures de puissance par zone ; ils ne rendent pas compte de la perception de l'oreille.",
])
titre("6.4 Améliorations possibles", 2)
puces([
    "Utiliser des filtres plus sélectifs, par exemple des filtres de Butterworth ou de Linkwitz-Riley d'ordre 4, "
    "qui réduisent le chevauchement des bandes tout en permettant une recombinaison sans coloration.",
    "Augmenter le nombre de bandes, ou proposer un égaliseur paramétrique (fréquence centrale et largeur réglables).",
    "Tester d'autres types de signaux : voix, musique acoustique, signaux synthétiques de référence.",
    "Ajouter une mesure de sonie perçue pour comparer les versions à volume perçu égal.",
])

# ---------------------------------------------------------------------------
# 7. Conclusion et références
# ---------------------------------------------------------------------------
titre("7. Conclusion")
para("Ce projet a permis de concevoir un égaliseur audio numérique à trois bandes, utilisable au travers "
     "d'une application dédiée. À partir d'un seul filtre élémentaire, le passe-bas par lissage exponentiel "
     "appliqué en aller-retour, les bandes des graves, des médiums et des aigus ont été construites de façon "
     "à garantir une reconstruction exacte du signal lorsque les gains sont nuls. Trois versions égalisées "
     "d'un extrait de 20 secondes ont été produites et comparées à l'original à l'aide des spectres, des "
     "formes d'onde et d'indicateurs de niveau. Les résultats confirment le fonctionnement de l'égaliseur et "
     "montrent sa principale limite : la pente douce des filtres provoque un chevauchement des bandes, qui "
     "écarte les variations obtenues des gains demandés. L'emploi de filtres d'ordre plus élevé constitue la "
     "suite naturelle de ce travail.")

# ---------------------------------------------------------------------------
# Annexes
# ---------------------------------------------------------------------------
saut_de_page()
titre("Annexes")
titre("Annexe A : organisation du code source", 2)
para("Le code est fourni dans le dossier du projet. Il se lance avec la commande streamlit run "
     "streamlit_app.py après installation des dépendances listées dans requirements.txt.")
tableau(
    ["Fichier ou dossier", "Rôle"],
    [
        ["streamlit_app.py", "Point d'entrée de l'application"],
        ["egaliseur/filtres.py", "Filtres : passe-bas, séparation en trois bandes, gains, recombinaison"],
        ["egaliseur/audio_io.py", "Lecture des fichiers WAV, extrait, spectre, export"],
        ["egaliseur/vues/", "Pages de l'application : Fichier, Bandes, Recombinaison"],
        ["scripts/generer_versions.py", "Production de l'extrait, des versions égalisées et des indicateurs"],
        ["tests/", "Tests automatiques (filtres, lecture et écriture des fichiers)"],
    ],
    [5.5, 10.5],
    "Organisation du code source.",
)
para("Extrait du fichier egaliseur/filtres.py :", alignement=WD_ALIGN_PARAGRAPH.LEFT)
code = (RACINE / "egaliseur" / "filtres.py").read_text(encoding="utf-8")
debut = code.index("CORRECTION_ALLER_RETOUR =")
fin = code.index("BACKEND:")
for ligne in code[debut:fin].rstrip().splitlines():
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(ligne if ligne else " ")
    run.font.name = "Courier New"
    run.font.size = Pt(8.5)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "Courier New")

titre("Annexe B : figures complémentaires", 2)
para("Détail des trois bandes pour chaque version : spectre (a) et forme d'onde (b), avant et après le gain.")
noms_bandes = {"graves": "graves", "mediums": "médiums", "aigus": "aigus"}
for numero in (1, 2, 3):
    for bande, nom in noms_bandes.items():
        figures_cote_a_cote(f"v{numero}_{bande}_spectre", f"v{numero}_{bande}_onde",
                            f"Version {numero}, bande des {nom} : (a) spectre ; (b) forme d'onde.", 7.4)

titre("Annexe C : fichiers remis", 2)
para("Tous les éléments remis sont rassemblés dans le dossier livrable :", alignement=WD_ALIGN_PARAGRAPH.LEFT)
tableau(
    ["Dossier", "Contenu"],
    [
        ["01_Rapport", "Le présent rapport (Word et PDF)"],
        ["02_Donnees_brutes", "Fichier original non modifié et extrait brut de 20 s"],
        ["03_Versions_egalisees", "Les trois versions égalisées (WAV) ; la version 2 a un niveau abaissé de 2,27 dB"],
        ["04_Graphiques", "Captures de l'application et schéma de la chaîne de traitement"],
        ["05_Parametres_et_indicateurs", "Fréquences de coupure, gains et indicateurs mesurés (CSV)"],
        ["06_Code_source", "Application, scripts de production des livrables et tests"],
    ],
    [5.5, 10.5],
    "Contenu du dossier livrable.",
)

SORTIE.parent.mkdir(parents=True, exist_ok=True)
doc.save(SORTIE)
print("Rapport :", SORTIE, "|", compteurs["figure"], "figures,", compteurs["tableau"], "tableaux")
