# Dataset: histology landmarks

[![Build Status](https://travis-ci.org/Borda/dataset-histology-landmarks.svg?branch=master)](https://travis-ci.org/Borda/dataset-histology-landmarks)
[![codecov](https://codecov.io/gh/Borda/dataset-histology-landmarks/branch/master/graph/badge.svg)](https://codecov.io/gh/Borda/dataset-histology-landmarks)
[![codebeat badge](https://codebeat.co/badges/3e86ad36-cb0c-430f-a096-a221ca871bb4)](https://codebeat.co/a/jirka-borovec/projects/github-com-borda-dataset-histology-landmarks-master)
[![Maintainability](https://api.codeclimate.com/v1/badges/e1374e80994253cc8e95/maintainability)](https://codeclimate.com/github/Borda/dataset-histology-landmarks/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/e1374e80994253cc8e95/test_coverage)](https://codeclimate.com/github/Borda/dataset-histology-landmarks/test_coverage)


**Dataset: landmarks for registration of [histology images](http://cmp.felk.cvut.cz/~borovji3/?page=dataset)**

The dataset consists of 2D histological microscopy tissue slices, stained with different stains. The main challenges for these images are the following: very large image size, appearance differences, and lack of distinctive appearance objects. Our dataset contains 108 image pars and manually placed landmarks for registration quality evaluation.

![reconstruction](figures/images-landmarks.jpg)

The image part of the dataset are available [here](http://cmp.felk.cvut.cz/~borovji3/?page=dataset). **Note** that the accompanied landmarks are the initial from a single a user and the precise landmarks should be obtained by fusion of several users even you can help and improve the annotations.

---

## Landmarks

The landmarks have standard [ImageJ](https://imagej.net/Welcome) structure and coordinate frame (the origin [0, 0] is located in top left corner of the image plane). For handling this landmarks we provide a simple macros for [import](annotations/multiPointSet_import.ijm) and [export](annotations/multiPointSet_export.ijm).

The landmark file is as follows:
```
 ,X,Y
1,226,173
2,256,171
3,278,182
4,346,207
...
```
 and it can be simply imported by `pandas`

The folder structure is the same as for images, so the landmarks share the same names with the image and they are located in the same directory next to images.

```
DATASET
 |- [set_name1]
 |  |- scale-[number1]pc
 |  |   |- [image_name1].jpg
 |  |   |- [image_name1].csv
 |  |   |- [image_name2].jpg
 |  |   |- [image_name2].csv
 |  |   |  ...
 |  |   |- [image_name].jpg
 |  |   '- [image_name].csv
 |  |- scale-[number2]pc
 |  |  ...
 |  '- scale-[number]pc
 |      |- [image_name1].png
 |      |- [image_name1].csv
 |      |  ...
 |      |- [image_name].png
 |      '- [image_name].csv
 |- [set_name2]
 | ...
 '- [set_name]
```

The landmarks for all images are generated as consensus over all user providing they annotation for a particular image set. 
```bash
python handlers/run_generate_landmarks.py \
    -a ./annotations -d ./dataset  --scales 10 25 50
```
All landmarks can be easy visualized as draw points over an image and also show image pairs and landmark pars where is expected that there is the main direction of displacement for all landmarks (estimating affine transformation).
```bash
python handlers/run_visualise_landmarks.py \
    -l ./dataset -i ./dataset -o ./output
```
There is a verification procedure before any new annotation is added the "authorised" annotation. First, see you did not swap any landmark or disorder them which can be simply observed from main movement direction for all landmarks in all image pairs in a particular sequence. Second, your annotation error should not be significantly larger than a reference.

---

## Annotations

The annotation is a collection of landmarks placement from several users. The structure is similar to the used in the dataset with the minor difference that there is user/author "name" and the annotation is made jut in a single scale.

![reconstruction](figures/imagej-image-pair.jpg)

Tutorial how to put landmarks in a set of images step by step:
1. Open **Fiji**
2. Load images (optimal is to open complete set)
3. Click relevant points (landmarks) in all images.
4. Exporting finally placed landmarks.
5. Importing existing landmarks if needed.

Structure of the annotation directory:
```
DATASET
 |- [set_name1]
 |  |- user-[initials1]_scale-[number2]pc
 |  |   |- [image_name1].csv
 |  |   |- [image_name2].csv
 |  |   |  ...
 |  |   '- [image_name].csv
 |  |- user-[initials2]_scale-[number1]pc
 |  |  ...
 |  |- user-[initials]_scale-[number]pc
 |  |   |- [image_name2].csv
 |  |   |  ...
 |  |   '- [image_name].csv
 |- [set_name2]
 | ...
 '- [set_name]
```

### Placement of relevant points

Because it is not possible to remove already placed landmarks, check if the partial stricture you want to annotate appears in all images before you place the first landmark in any image:
1. Select `Multi-point tool`, note that the points are indexed so you can verify that the actual points are fine.
2. To move in the image use Move tool and also Zoom to see the details.
3. Put points (landmarks) to the important parts of the tissue like edges of a centroid of bubbles appearing in all cuts of the tissue. Each image should contain about 80 landmarks.

![reconstruction](figures/landmarks-zoom.jpg)

### Work with Export / Import macros

**Exporting finally placed landmarks**
When all landmarks are placed on all images, export each of them into separate files.
1. Install macro for export landmarks, such that select `Plugins -> Marcos -> Instal...`
then select exporting macro `annotations/multiPointSet_export.ijm`.
2. Select one image and click `Plugins -> Marcos -> exportMultipointSet`.
3. Chose a name the landmark file to be same as the image name without any annex.
4. The macro automatically exports all landmarks from the image in `.csv` format into chosen directory.

**Importing existing landmarks**
For concretion already made landmarks or continuation from last time, importing landmarks would be needed to restore landmarks from a file (Note, the macro uses `.csv` format).
1. Install importing macro `annotations/multiPointSet_import.ijm`.
2. Select one image and click
`Plugins -> Marcos -> importMultipointSet`.
3. Then you select demanded landmarks by its name.


### Validation

When the landmark placement phase is done, we need to check all landmarks are correct. 
We also compute statistic of landmarks annotation of each user to the consensus and save it into a file. Then you should have focused on landmarks where STD or maximal value exceed a usual value.
```bash
python handlers/run_evaluate_landmarks.py \
    -a ./annotations -o ./output
```
If you find such suspicious annotation, perform a visual inspection
```bash
python handlers/run_visualise_landmarks.py \
    -l ./annotations -i ./dataset -o ./output
```

In the visualization, the landmarks pairs in both images are connected by a line. 
We compute an affine transformation in between the two sets of landmarks and error between landmarks in the second image and warped landmarks from the first image. 
Then we landmarks are connected by a straight line if the error is larger then a 5 STD we consider them as suspicions (wrong localization or large elastic deformation). 
Otherwise the pair is connected by a dotted line.

![landmarks-pairs](figures/PAIR___29-041-Izd2-w35-CD31-3-les3_tif-Fused___AND___29-041-Izd2-w35-proSPC-4-les3_tif-Fused.jpg)

---

## References

J. Borovec, A. Munoz-Barrutia, and J. Kybic, “**Benchmarking of image registration methods for differently stained histological slides**” in IEEE International Conference on Image Processing (ICIP), 2018.
