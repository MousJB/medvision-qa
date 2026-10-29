# Expérience IRM réelle : figshare (Jun Cheng), deux versions, évaluation MedVision QA

Protocole fixé avant entraînement : [PROTOCOL.md](PROTOCOL.md) et
[figshare_eval/config.toml](figshare_eval/config.toml) (commit `6de2a12`). Sources et
licences : [docs/phase4_data_sources.md](../../docs/phase4_data_sources.md).

> Données : figshare « brain tumor dataset », Jun Cheng, v8, **CC BY 4.0**,
> DOI [10.6084/m9.figshare.1512427.v8](https://doi.org/10.6084/m9.figshare.1512427.v8).
> Aucune image n'est versionnée ici ; seuls des identifiants, hashes et agrégats le sont.

## Reproduire

```bash
python -m venv .venv-train
.venv-train\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
.venv-train\Scripts\python -m pip install h5py pillow kagglehub numpy scipy
.venv-train\Scripts\python -m pip install -e . --no-deps

.venv-train\Scripts\python experiments/brain_mri/download_figshare.py     # MD5 vérifiés
.venv-train\Scripts\python experiments/brain_mri/prepare_figshare.py      # PNG, manifeste, séparation, audit
.venv-train\Scripts\python experiments/brain_mri/train.py simplecnn
.venv-train\Scripts\python experiments/brain_mri/train.py resnet18
python -m medvision_qa experiments/brain_mri/figshare_eval/config.toml -o experiments/brain_mri/figshare_eval/report.html
```

## 1. Préparation et audit des données

| Élément | Résultat |
|---|---|
| Fichiers | 3 064 `.mat` (MATLAB v7.3 / HDF5), lus avec h5py : champs `label`, `PID`, `image` uniquement |
| Tailles | 3 049 en 512×512, 15 en 256×256 |
| PID bruts | 233 ; aucun PID associé à deux classes |
| Doublons exacts (pixels) | **0** |
| Quasi-doublons (pHash, distance ≤ 4) | 724 paires, très majoritairement des coupes voisines d'un même patient |

### Constat : un même patient sous plusieurs PID

Les PID de forme `MR<nombre><lettre>` (43 PID, tous des gliomes) forment **18 familles
de même racine** (par ex. `MR024780B`, `D`, `E`, `G`). Avec la séparation par PID brut,
**12 familles se retrouvaient réparties entre entraînement, validation et test.**

Inspection visuelle (planches dans `data/inspection/`, non versionnées) : les coupes de
`MR024780D` (test) et `MR024780E` (entraînement) sont quasi identiques (même tête, même
lésion). `MR049453` / `MR049453B`, `MR051644B` / `MR051644C` et `MR040240` /
`MR040240D` montrent la même anatomie et la même lésion, avec des différences
compatibles avec des examens à des dates différentes. Ce n'est pas une expertise
radiologique.

**Décision (écart au protocole, pris avant tout entraînement)** : un patient = la racine
du PID. On passe à 209 patients, et la séparation donne **125 / 20 / 64 patients**
(1 996 / 292 / 776 images). C'est le choix prudent : fusionner à tort deux patients ne
fait que réduire l'échantillon, alors que les laisser séparés risquait une fuite vers le
test. Les critères d'acceptation n'ont pas changé.

### Quasi-doublons entre patients différents : faux positifs

Après regroupement, 69 paires relient des patients différents, dont 38 entre des jeux
différents. **Les 38 paires ont toutes été inspectées** : les lésions, les têtes et les
contrastes diffèrent ; seule l'orientation de coupe (sagittale médiane, axiale) se
ressemble, et 11 de ces paires associent même un méningiome à un gliome. Le pHash à seuil 4 est
trop permissif pour l'IRM cérébrale : il signale des ressemblances, il ne prouve rien.

Détails : [figshare_eval/data_audit.json](figshare_eval/data_audit.json),
[figshare_eval/manifest.csv](figshare_eval/manifest.csv).

## 2. Audit du dataset Kaggle MRI-BT (celui de `brain-tumor-mri-classification`)

Script : [audit_mri_bt.py](audit_mri_bt.py). Résultats :
[mri_bt_audit/summary.json](mri_bt_audit/summary.json) et
[mri_bt_audit/flagged_pairs.csv](mri_bt_audit/flagged_pairs.csv) (noms de fichiers
seulement : aucune image n'est versionnée, la licence de Br35H n'étant pas ouverte).
Périmètre : le jeu original BT-MRI (Training 5 712, Testing 1 311, toutes les images en
224×224). Les jeux « Challenging » sont exclus, puisqu'ils sont par construction des
dégradations des mêmes images.

| Constat | Valeur |
|---|---|
| Groupes de fichiers **identiques à l'octet** | 300 (695 paires) |
| Paires identiques **Training ↔ Testing** | 365 |
| **Images de Testing ayant une copie identique dans Training** | **216 / 1 311 (16,5 %)** : méningiome 106, no-tumor 105, hypophyse 5 |
| Doublons identiques portant des étiquettes différentes | 0 |
| Quasi-doublons (pHash ≤ 4) à étiquettes différentes | 50 ; **24 inspectées** : toutes montrent des images différentes, donc des faux positifs (les 26 autres n'ont pas été inspectées) |
| Images MRI-BT proches d'une image figshare (pHash ≤ 4) | 1 704 (surtout méningiome et hypophyse de Training), étiquettes concordantes dans 98 % des paires |

**Ce que l'on peut affirmer.** 16,5 % des images de test de MRI-BT sont des copies exactes
d'images d'entraînement. Une évaluation sur ce découpage Training/Testing n'est donc pas
indépendante pour ces images, et les performances publiées sur ce découpage (y compris
celles du README de `brain-tumor-mri-classification`) sont probablement optimistes.
L'ampleur de ce biais n'a pas été mesurée.

**Ce que l'on ne peut pas affirmer.** Un fichier identique prouve une image identique,
pas l'identité d'un patient. L'absence de `patient_id` dans MRI-BT empêche de vérifier si
d'autres coupes d'un même patient sont réparties entre les deux jeux. La correspondance
avec figshare (1 704 images) est cohérente avec l'hypothèse d'un assemblage incluant
figshare, sans la prouver à elle seule.

## 3. Entraînement des deux versions

| | A — SimpleCNN | B — ResNet18 (ImageNet) |
|---|---|---|
| Meilleure époque (macro-F1 de validation) | 13 (0,850) | 15 (0,954) |
| Durée (GTX 1650) | 169 s | 196 s |
| SHA-256 des poids | `7b17a4a3…5127d2` | `a8901dd2…25d73f5` |
| Journal complet | [training_simplecnn.json](figshare_eval/training_simplecnn.json) | [training_resnet18.json](figshare_eval/training_resnet18.json) |

Environnement : torch 2.14.1+cu126, torchvision, Python 3.12.6. Les poids ne sont pas
versionnés ; ils sont dans `data/models/` et identifiés par leur SHA-256.

**Code.** Les journaux d'entraînement indiquent `code_commit = dedb768`, qui était le HEAD au
moment de l'exécution, alors que `train.py` n'était pas encore commité. Le code exécuté a
été commité sans modification dans `2bcfb77` : contenu identique, vérifié par SHA-256
après normalisation des fins de ligne. C'est ce commit qui est déclaré dans
`config.toml`.

**Déterminisme partiel.** Les graines sont fixées et les algorithmes déterministes sont
demandés (`warn_only`), mais certaines opérations CUDA n'ont pas de version déterministe.
Un nouvel entraînement peut donc donner des poids légèrement différents.

## 4. Évaluation MedVision QA (test : 776 coupes, 64 patients)

Rapport : [figshare_eval/report.html](figshare_eval/report.html). Commande :
`python -m medvision_qa experiments/brain_mri/figshare_eval/config.toml -o …`.
Intervalles à 95 %, bootstrap percentile **par patient** (64 unités), 2 000 tirages.

| Critère (fixé avant entraînement) | Résultat | État |
|---|---|---|
| C1 — macro-F1 de B non inférieure à A (marge 0,03) | Δ = +0,129, IC [0,074 ; 0,188] | **SATISFIED** |
| C2 — sensibilité gliome de B ≥ 0,90 | 0,929, IC [0,865 ; 0,970] | **INCONCLUSIVE** |
| C3 — AUROC gliome de B supérieure à A | 0,916 → 0,990, Δ IC [0,031 ; 0,135] | **SATISFIED** |
| **Décision globale** | | **INCONCLUSIVE** |

| Métrique | A — SimpleCNN | B — ResNet18 |
|---|---|---|
| Accuracy | 0,800 [0,730 ; 0,860] | 0,928 [0,875 ; 0,968] |
| Macro-F1 | 0,795 [0,717 ; 0,851] | 0,923 [0,867 ; 0,964] |
| Rappel gliome / méningiome / hypophyse | 0,800 / 0,750 / 0,835 | 0,929 / 0,934 / 0,923 |
| Spécificité (gliome contre autres) | 0,844 | 0,969 |
| AUROC (gliome contre autres) | 0,916 | 0,990 |

**Lecture.** B est nettement meilleure que A sur ces données. Mais **C2 n'est pas
démontré** : l'estimation de la sensibilité gliome (0,929) dépasse 0,90, alors que
l'intervalle, avec 64 patients, contient encore 0,90. Conclure « OK » sur l'estimation
ponctuelle serait une sur-interprétation, et c'est ce que l'état INCONCLUSIVE empêche.
Pour trancher, il faudrait davantage de patients de test, ou un critère et une
justification de taille d'échantillon définis en conséquence.

McNemar n'est **pas applicable** (plusieurs coupes par patient). DeLong n'est pas
implémenté ; la différence d'AUROC vient du bootstrap apparié.

## 5. Limites

- Un seul dataset (2 hôpitaux chinois, acquisitions de 2005 à 2010, T1 avec gadolinium) :
  aucune validation externe, et les résultats ne se transfèrent pas à d'autres
  acquisitions.
- Le regroupement des PID repose sur une hypothèse (même racine = même patient) étayée
  par une inspection visuelle non experte.
- Validation de 20 patients : la sélection de l'époque est bruitée (la macro-F1 de
  validation de A varie de 0,54 à 0,85 d'une époque à l'autre).
- Le min-max par image et le passage en 224×224 perdent de l'information. Aucun réglage
  d'hyperparamètres n'a été fait : ce n'est pas une comparaison optimisée des deux
  architectures.
- Pas de tests de robustesse sur ces modèles. Les jeux « Challenging » de MRI-BT ont 4
  classes (dont notumor) et ne correspondent pas à la tâche figshare à 3 classes.
- Aucune de ces analyses n'est une validation clinique.
