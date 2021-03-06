"""
General utils used for this collection of scripts

Copyright (C) 2014-2018 Jiri Borovec <jiri.borovec@fel.cvut.cz>
"""


import os
import re
import glob
import logging
import multiprocessing as mproc

import tqdm
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pylab as plt

NB_THREADS = max(1, int(mproc.cpu_count() * 0.9))
SCALES = [5, 10, 25, 50, 100]
# template nema for scale folder
TEMPLATE_FOLDER_SCALE = 'scale-%dpc'
# regular expresion patters for determining scale and user
REEXP_FOLDER_ANNOT = 'user-(.\S+)_scale-(\d+)pc'
REEXP_FOLDER_SCALE = '\S*scale-(\d+)pc'
# default figure size for visualisations
FIGURE_SIZE = 18
# expected image extensions
IMAGE_EXT = ['.png', '.jpg', '.jpeg']
COLORS = 'grbm'


def update_path(path, max_depth=5):
    """ bobble up to find a particular path

    :param str path:
    :param int max_depth:
    :return str:

    >>> os.path.isdir(update_path('handlers'))
    True
    >>> os.path.isdir(update_path('no-handlers'))
    False
    """
    path_in = path
    if path.startswith('/'):
        return path
    for _ in range(max_depth):
        if os.path.exists(path):
            break
        path = os.path.join('..', path)

    path = os.path.abspath(path) if os.path.exists(path) else path_in
    return path


def wrap_execute_parallel(wrap_func, iterate_vals,
                          nb_jobs=NB_THREADS, desc=''):
    """ wrapper for execution parallel of single thread as for...

    :param wrap_func: function which will be excited in the iterations
    :param [] iterate_vals: list or iterator which will ide in iterations
    :param int nb_jobs: number og jobs running in parallel
    :param str desc: description for the bar

    >>> [o for o in wrap_execute_parallel(lambda pts: pts ** 2, range(5), nb_jobs=1)]
    [0, 1, 4, 9, 16]
    >>> [o for o in wrap_execute_parallel(sum, [[0, 1]] * 5, nb_jobs=2)]
    [1, 1, 1, 1, 1]
    """
    iterate_vals = list(iterate_vals)

    tqdm_bar = tqdm.tqdm(total=len(iterate_vals), desc=desc)

    if nb_jobs > 1:
        logging.debug('perform sequential in %i threads', nb_jobs)
        pool = mproc.Pool(nb_jobs)

        for out in pool.imap_unordered(wrap_func, iterate_vals):
            yield out
            if tqdm_bar is not None:
                tqdm_bar.update()
        pool.close()
        pool.join()
    else:
        for out in map(wrap_func, iterate_vals):
            yield out
            if tqdm_bar is not None:
                tqdm_bar.update()


def create_folder(path_base, folder):
    path_folder = os.path.join(path_base, folder)
    if not os.path.isdir(path_folder):
        os.mkdir(path_folder)
    return path_folder


def parse_path_user_scale(path):
    """ from given path with annotation parse user name and scale

    :param str path: path to the user folder
    :return (str, int):

    >>> parse_path_user_scale('user-KO_scale-.5pc')
    ('', nan)
    >>> parse_path_user_scale('user-JB_scale-50pc')
    ('JB', 50)
    >>> parse_path_user_scale('sample/path/user-ck6_scale-25pc')
    ('ck6', 25)
    """
    path = os.path.basename(path)
    obj = re.match(REEXP_FOLDER_ANNOT, path)
    if obj is None:
        return '', np.nan
    user, scale = obj.groups()
    scale = int(scale)
    return user, scale


def parse_path_scale(path):
    """ from given path with annotation parse scale

    :param str path: path to the user folder
    :return int:

    >>> parse_path_scale('scale-.1pc')
    nan
    >>> parse_path_scale('user-JB_scale-50pc')
    50
    >>> parse_path_scale('scale-10pc')
    10
    """
    path = os.path.basename(path)
    obj = re.match(REEXP_FOLDER_SCALE, path)
    if obj is None:
        return np.nan
    scale = int(obj.groups()[0])
    return scale


def landmarks_consensus(list_landmarks):
    """ compute consensus as mean over all landmarks

    :param [DF] list_landmarks: list of DataFrames
    :return DF:

    >>> lnds1 = pd.DataFrame(np.zeros((5, 2)), columns=['X', 'Y'])
    >>> lnds2 = pd.DataFrame(np.ones((6, 2)), columns=['X', 'Y'])
    >>> landmarks_consensus([lnds1, lnds2])
         X    Y
    0  0.5  0.5
    1  0.5  0.5
    2  0.5  0.5
    3  0.5  0.5
    4  0.5  0.5
    5  1.0  1.0
    """
    lens = [len(lnd) for lnd in list_landmarks]
    df = list_landmarks[np.argmax(lens)]
    lens = sorted(set(lens), reverse=True)
    for l in lens:
        for ax in ['X', 'Y']:
            df[ax][:l] = np.mean([lnd[ax].values[:l]
                                  for lnd in list_landmarks
                                  if len(lnd) >= l], axis=0)
    return df


def collect_triple_dir(list_path_lnds, path_dataset, path_out, coll_dirs=None):
    """ collect all subdir up to level of scales

    :param list_path_lnds:
    :param path_dataset:
    :param path_out:
    :param coll_dirs:
    :return:

    >>> coll_dirs, d = collect_triple_dir([update_path('annotations')],
    ...                                   update_path('dataset'), 'output')
    >>> len(coll_dirs) > 0
    True
    >>> 'annotations' in coll_dirs[0]['landmarks'].split(os.sep)
    True
    >>> 'dataset' in coll_dirs[0]['images'].split(os.sep)
    True
    >>> 'output' in coll_dirs[0]['output'].split(os.sep)
    True
    >>> d
    []
    """
    if coll_dirs is None:
        coll_dirs = []
    for path_lnds in list_path_lnds:
        set_name, scale_name = path_lnds.split(os.sep)[-2:]
        scale = parse_path_scale(scale_name)
        if np.isnan(scale):
            sub_dirs = sorted([p for p in glob.glob(os.path.join(path_lnds, '*'))
                               if os.path.isdir(p)])
            coll_dirs, sub_dirs = collect_triple_dir(sub_dirs, path_dataset,
                                                     path_out, coll_dirs)
            continue
        coll_dirs.append({
            'landmarks': path_lnds,
            'images': os.path.join(path_dataset, set_name,
                                   TEMPLATE_FOLDER_SCALE % scale),
            'output': os.path.join(path_out, set_name, scale_name)
        })
    return coll_dirs, []


def estimate_affine_transform(points_0, points_1):
    """ estimate Affine transformations and warp particular points sets
    to the other coordinate frame

    :param ndarray points_0: set of points
    :param ndarray points_1: set of points
    :return (ndarray, ndarray, ndarray): transform. matrix and warped point sets

    >>> pts0 = np.array([[4., 116.], [4., 4.], [26., 4.], [26., 116.]], dtype=int)
    >>> pts1 = np.array([[61., 56.], [61., -56.], [39., -56.], [39., 56.]])
    >>> matrix, pts0_w, pts1_w = estimate_affine_transform(pts0, pts1)
    >>> np.round(matrix, 2)
    array([[ -1.,   0.,  -0.],
           [  0.,   1.,  -0.],
           [ 65., -60.,   1.]])
    >>> pts0_w
    array([[ 61.,  56.],
           [ 61., -56.],
           [ 39., -56.],
           [ 39.,  56.]])
    >>> pts1_w
    array([[   4.,  116.],
           [   4.,    4.],
           [  26.,    4.],
           [  26.,  116.]])
    """
    # SEE: https://stackoverflow.com/questions/20546182
    nb = min(len(points_0), len(points_1))
    # Pad the data with ones, so that our transformation can do translations
    pad = lambda pts: np.hstack([pts, np.ones((pts.shape[0], 1))])
    unpad = lambda pts: pts[:, :-1]
    x = pad(points_0[:nb])
    y = pad(points_1[:nb])

    # Solve the least squares problem X * A = Y to find our transform. matrix A
    matrix, res, rank, s = np.linalg.lstsq(x, y)

    transform = lambda pts: unpad(np.dot(pad(pts), matrix))
    points_0_warp = transform(points_0)

    transform_inv = lambda pts: unpad(np.dot(pad(pts), np.linalg.pinv(matrix)))
    points_1_warp = transform_inv(points_1)

    return matrix, points_0_warp, points_1_warp


def estimate_landmark_outliers(points_0, points_1, std_coef=5):
    """ estimated landmark outliers after affine alignment

    :param ndarray points_0: set ot points
    :param ndarray points_1: set ot points
    :param float std_coef:
    :return ([bool], [float]): vector or binary outliers and computed error

    >>> lnds0 = np.array([[4., 116.], [4., 4.], [26., 4.], [26., 116.],
    ...                   [18, 45], [0, 0], [-12, 8], [1, 1]])
    >>> lnds1 = np.array([[61., 56.], [61., -56.], [39., -56.], [39., 56.],
    ...                   [47., -15.], [65., -60.], [77., -52.], [0, 0]])
    >>> out, err = estimate_landmark_outliers(lnds0, lnds1, std_coef=3)
    >>> out.astype(int)
    array([0, 0, 0, 0, 0, 0, 0, 1])
    >>> np.round(err, 2)
    array([  1.02,  16.78,  10.29,   5.47,   6.88,  18.52,  20.94,  68.96])
    """
    nb = min(len(points_0), len(points_1))
    _, points_0w, _ = estimate_affine_transform(points_0[:nb], points_1[:nb])
    err = np.sqrt(np.sum((points_1[:nb] - points_0w) ** 2, axis=1))
    norm = np.std(err) * std_coef
    out = (err > norm)
    return out, err


def compute_landmarks_statistic(landmarks_ref, landmarks_in, use_affine=False):
    """ compute statistic on errors between reference and sensed landamrks

    :param ndarray landmarks_ref:
    :param ndarray landmarks_in:
    :param bool use_affine:
    :return:

    >>> lnds0 = np.array([[4., 116.], [4., 4.], [26., 4.], [26., 116.],
    ...                   [18, 45], [0, 0], [-12, 8], [1, 1]])
    >>> lnds1 = np.array([[61., 56.], [61., -56.], [39., -56.], [39., 56.],
    ...                   [47., -15.], [65., -60.], [77., -52.], [0, 0]])
    >>> d_stat = compute_landmarks_statistic(lnds0, lnds1, use_affine=True)
    >>> [(k, np.round(d_stat[k])) for k in sorted(d_stat)]  # doctest: +NORMALIZE_WHITESPACE
    [('count', 8.0),
     ('image_diagonal', 86.0),
     ('image_size', array([ 65.,  56.])),
     ('max', 69.0),
     ('mean', 19.0),
     ('median', 14.0),
     ('min', 1.0),
     ('std', 21.0)]
    >>> d_stat = compute_landmarks_statistic(lnds0, lnds1)
    >>> d_stat['mean']  # doctest: +ELLIPSIS
    69.0189...
    """
    if isinstance(landmarks_ref, pd.DataFrame):
        landmarks_ref = landmarks_ref[['X', 'Y']].values
    if isinstance(landmarks_in, pd.DataFrame):
        landmarks_in = landmarks_in[['X', 'Y']].values

    if use_affine:
        _, err = estimate_landmark_outliers(landmarks_ref, landmarks_in)
    else:
        nb = min(len(landmarks_ref), len(landmarks_in))
        err = np.sqrt(np.sum((landmarks_ref[:nb] - landmarks_in[:nb]) ** 2,
                             axis=1))
    df_err = pd.DataFrame(err)
    df_stat = df_err.describe().T[['count', 'mean', 'std', 'min', 'max']]
    d_stat = dict(df_stat.iloc[0])
    d_stat['median'] = np.median(err)

    landmarks = np.concatenate([landmarks_ref, landmarks_in], axis=0)
    im_size = (np.max(landmarks, axis=0) + np.min(landmarks, axis=0))
    d_stat['image_size'] = im_size.tolist()
    d_stat['image_diagonal'] = np.sqrt(np.sum(im_size ** 2))

    return d_stat


def create_consensus_landmarks(path_annots, equal_size=True):
    """ create a consesus on set of landmarks

    :param [str] path_annots:
    :param bool equal_size:
    :return {str: DF}:
    """
    dict_list_lnds = {}
    # find all landmars for particular image
    for p_annot in path_annots:
        _, scale = parse_path_user_scale(p_annot)
        list_csv = glob.glob(os.path.join(p_annot, '*.csv'))
        for p_csv in list_csv:
            name = os.path.basename(p_csv)
            if name not in dict_list_lnds:
                dict_list_lnds[name] = []
            df_base = pd.read_csv(p_csv, index_col=0) / (scale / 100.)
            dict_list_lnds[name].append(df_base)

    dict_lnds, dict_lens = {}, {}
    # create consensus over particular landmarks
    for name in dict_list_lnds:
        dict_lens[name] = len(dict_list_lnds[name])
        # cases where the number od points is different
        df = landmarks_consensus(dict_list_lnds[name])
        dict_lnds[name] = df

    # take the minimal set or landmarks over whole set
    if equal_size and len(dict_lnds) > 0:
        nb_min = min([len(dict_lnds[n]) for n in dict_lnds])
        dict_lnds = {n: dict_lnds[n][:nb_min] for n in dict_lnds}

    return dict_lnds, dict_lens


def create_figure(im_size, max_fig_size=FIGURE_SIZE):
    norm_size = np.array(im_size) / float(np.max(im_size))
    # reverse dimensions and scale by fig size
    fig_size = norm_size[::-1] * max_fig_size
    fig, ax = plt.subplots(figsize=fig_size)
    return fig, ax


def format_figure(fig, ax, im_size, lnds):
    ax.set_xlim([min(0, np.min(lnds[1])), max(im_size[1], np.max(lnds[1]))])
    ax.set_ylim([max(im_size[0], np.max(lnds[0])), min(0, np.min(lnds[0]))])
    fig.tight_layout()
    return fig


def figure_image_landmarks(landmarks, image, max_fig_size=FIGURE_SIZE):
    """ create a figure with images and landmarks

    :param ndarray landmarks: landmark coordinates
    :param ndarray image: 2D image
    :param int max_fig_size:
    :return Figure:

    >>> np.random.seed(0)
    >>> lnds = np.random.randint(-10, 25, (10, 2))
    >>> img = np.random.random((20, 30))
    >>> fig = figure_image_landmarks(lnds, img)
    >>> isinstance(fig, matplotlib.figure.Figure)
    True
    >>> df_lnds = pd.DataFrame(lnds, columns=['X', 'Y'])
    >>> fig = figure_image_landmarks(df_lnds, None)
    >>> isinstance(fig, matplotlib.figure.Figure)
    True
    """
    if isinstance(landmarks, pd.DataFrame):
        landmarks = landmarks[['X', 'Y']].values
    if image is None:
        image = np.zeros(np.max(landmarks, axis=0) + 25)

    fig, ax = create_figure(image.shape[:2], max_fig_size)

    ax.imshow(image)
    ax.plot(landmarks[:, 0], landmarks[:, 1], 'go')
    ax.plot(landmarks[:, 0], landmarks[:, 1], 'r.')

    for i, lnd in enumerate(landmarks):
        ax.text(lnd[0] + 5, lnd[1] + 5, str(i + 1), fontsize=11, color='black')

    fig = format_figure(fig, ax, image.shape[:2], landmarks)

    return fig


def figure_pair_images_landmarks(pair_landmarks, pair_images, names=None,
                                 max_fig_size=FIGURE_SIZE):
    """ create a figure with image pair and connect related landmarks by line

    :param (ndarray) pair_landmarks: set of landmark coordinates
    :param (ndarray) pair_images: set of 2D image
    :param [str] names: names
    :param int max_fig_size:
    :return Figure:

    >>> np.random.seed(0)
    >>> lnds = np.random.randint(-10, 25, (10, 2))
    >>> img = np.random.random((20, 30))
    >>> fig = figure_pair_images_landmarks((lnds, lnds + 5), (img, img))
    >>> isinstance(fig, matplotlib.figure.Figure)
    True
    >>> df_lnds = pd.DataFrame(lnds, columns=['X', 'Y'])
    >>> fig = figure_pair_images_landmarks((df_lnds, df_lnds), (img, None))
    >>> isinstance(fig, matplotlib.figure.Figure)
    True
    """
    assert len(pair_landmarks) == len(pair_images), \
        'not equal counts for images (%i) and landmarks (%i)' \
        % (len(pair_landmarks), len(pair_images))
    pair_landmarks = list(pair_landmarks)
    pair_images = list(pair_images)
    for i, landmarks in enumerate(pair_landmarks):
        if isinstance(landmarks, pd.DataFrame):
            pair_landmarks[i] = landmarks[['X', 'Y']].values
    for i, image in enumerate(pair_images):
        if image is None:
            pair_images[i] = np.zeros(np.max(pair_landmarks[i], axis=0) + 25)

    im_size = np.max([img.shape[:2] for img in pair_images], axis=0)
    fig, ax = create_figure(im_size, max_fig_size)

    # draw semi transparent images
    for image in pair_images:
        ax.imshow(image, alpha=(1. / len(pair_images)))

    # draw lined between landmarks
    for i, lnds1 in enumerate(pair_landmarks[1:]):
        lnds0 = pair_landmarks[i]
        outliers, _ = estimate_landmark_outliers(lnds0, lnds1)
        for (x0, y0), (x1, y1), out in zip(lnds0, lnds1, outliers):
            ln = '-' if out else '-.'
            ax.plot([x0, x1], [y0, y1], ln, color=COLORS[i % len(COLORS)])

    if names is None:
        names = ['image %i' % i for i in range(len(pair_landmarks))]
    # draw all landmarks
    for i, landmarks in enumerate(pair_landmarks):
        ax.plot(landmarks[:, 0], landmarks[:, 1], 'o',
                color=COLORS[i % len(COLORS)], label=names[i])

    assert len(pair_landmarks) > 0, 'missing any landmarks'
    for i, lnd in enumerate(pair_landmarks[0]):
        ax.text(lnd[0] + 5, lnd[1] + 5, str(i + 1), fontsize=11, color='black')

    ax.legend()

    fig = format_figure(fig, ax, im_size, ([lnds[0] for lnds in pair_landmarks],
                                           [lnds[1] for lnds in pair_landmarks]))

    return fig
