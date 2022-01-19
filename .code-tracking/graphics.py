import hashlib
from PIL import Image
from scipy.ndimage.filters import gaussian_filter
import requests
from io import BytesIO
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import seaborn as sns

import shutil

GAP = 48


def imscatter(x, y, image, ax=None, zoom=1):
    if ax is None:
        ax = plt.gca()
    im = OffsetImage(image, zoom=zoom)
    x, y = np.atleast_1d(x, y)
    artists = []
    for x0, y0 in zip(x, y):
        ab = AnnotationBbox(im, (x0, y0), xycoords='data', frameon=False)
        artists.append(ax.add_artist(ab))
    ax.update_datalim(np.column_stack([x, y]))
    ax.autoscale()
    return artists


def crop(img, size, color=(255, 0, 0), border=5):
    half = size // 2
    grid = np.array(
        np.meshgrid(np.arange(-half, half), np.arange(-half, half))).T
    distances = np.linalg.norm(grid, axis=-1)
    data = np.array(img)
    if img.mode != 'RGBA':
        data = np.dstack((data, np.ones(
            (size, size, 1), dtype=np.int16) * 255))

    mask = np.zeros_like(data)
    mask[distances > (half - border)] = color + (255, )
    mask[distances > half] = (255, 255, 255, 0)
    mask[:, :, 3] = gaussian_filter(mask[:, :, 3], sigma=1.76)
    data[distances > (half - border)] = mask[distances > (half - border)]
    return data


def gravatar(email, size=180, color=(255, 0, 0), border=5):
    size = int(size)
    hash = hashlib.md5(email.lower().strip().encode('utf-8')).hexdigest()
    url = f"https://0.gravatar.com/avatar/{hash}?s={size}"
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    return crop(img, size, color=color, border=border)


def extract_plot_data(cache, GAP=GAP):
    lengths = {}
    plot_data = {}
    for user, commits in cache.commits.items():
        count = len(set(commits))
        days = list(range(1, 1 + count))
        plot_data[user] = [
            [],
            days,
        ]
        for day in days:
            group = lengths.get(day, [])
            group.append((count, user))
            lengths[day] = group

    for (day, users) in lengths.items():
        users.sort()
        for i, (_, user) in enumerate(users):
            plot_data[user][0].append(GAP * i)
    return plot_data


def generate_images(cache: 'Cache', filename: str = "days.png",
                    GAP: int = GAP):
    plot_data = extract_plot_data(cache, GAP=GAP)
    max_count = max(list(map(lambda x: len(x[0]), plot_data.values())) + [0])

    colors = [
        (tuple(int(c * 255) for c in color), color)
        for color in sns.color_palette("pastel", n_colors=len(plot_data))
    ]
    sns.set_style("whitegrid")

    fig, ax = plt.subplots(
        figsize=(max_count + 5, len(plot_data) + 3),
        dpi=GAP * 2,
        facecolor='w',
        edgecolor='k')
    for (user, data), (color, c) in zip(plot_data.items(), colors):
        plt.scatter(data[1], data[0], color=c, label=user)
        imscatter(
            data[1],
            data[0],
            gravatar(cache.authors[user], color=color, size=GAP * 2),
            ax=ax)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    plt.legend()
    plt.xlim(0, max_count + 1)
    plt.xticks(
        ticks=range(1, max_count + 1),
        labels=list(map(lambda x: f"Day {x}", range(1, max_count + 1))))
    plt.ylim(-GAP // 2, (len(plot_data) - 0.5) * GAP)
    ax.axes.get_yaxis().set_visible(False)

    plt.savefig(filename)


def get_badges(cache: 'Cache', contrib_color="green", days_color="blue"):
    plot_data = extract_plot_data(cache)
    contributor_count = len(plot_data)
    days_count = sum(map(lambda x: len(x[0]), plot_data.values()))
    badges = {
        "contributors.svg.gz":
        f"https://img.shields.io/badge/contributors-{contributor_count}-{contrib_color}",
        "days.svg.gz":
        f"https://img.shields.io/badge/total%20days%20coded-{days_count}-{days_color}"
    }
    for (name, badge) in badges.items():
        response = requests.get(badge, stream=True)
        with open(name, 'wb') as file:
            shutil.copyfileobj(response.raw, file)
        del response
