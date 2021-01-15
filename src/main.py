# Imports
# -- Standard
from collections import Counter
from copy import deepcopy
from itertools import combinations
from pathlib import Path

# -- Third-Party
from numpy import array
from PIL import Image

# -- Application

# Config
# -- Paths
PROJECT_ROOT = Path(__file__).parent.parent
JIGSAWS_ROOT = PROJECT_ROOT / 'jigsaws'
OUTPUT_ROOT = PROJECT_ROOT / 'output'


def get_jigsaws():
    jigsaws_dict = {}
    for jigsaw_path in JIGSAWS_ROOT.glob('*'):
        jigsaws_dict[jigsaw_path.name] = []
        for jigsaw_piece_path in jigsaw_path.glob('*'):
            jigsaw_piece_image = Image.open(jigsaw_piece_path)

            jigsaw_piece = JigsawPiece(
                name=jigsaw_piece_path.stem,
                image=jigsaw_piece_image
            )
            trivial_jigsaw = Jigsaw(pieces=[jigsaw_piece])

            jigsaws_dict[jigsaw_path.name].append(trivial_jigsaw)
    return jigsaws_dict


class InvalidJigsaw(Exception):
    pass


class Boundary:
    def __init__(self, pixels, pos):
        self.pixels = pixels
        self._pos = pos
        self.is_internal = False

    @property
    def pos(self):
        return self._pos

    def is_compatible_with(self, other):
        return len(self.pixels) == len(other.pixels)

    def compare_difference_with(self, other):
        difference = 0
        for i in range(len(self.pixels)):
            for j in range(3):
                difference += (self.pixels[i][j] - other.pixels[i][j]) ** 2
        return difference

    def update_pos(self, parent_pos, parent_new_pos):
        self._pos = self._pos - parent_pos + parent_new_pos


class Jigsaw:
    def __init__(self, pieces):
        self.pieces = pieces

    @property
    def name(self):
        return '-'.join([piece.name for piece in self.pieces])

    @property
    def image(self):
        image = Image.new('RGB', (self.width, self.height))
        for piece in self.pieces:
            shifted_image_pos_x = int((piece.pos[0] - self.top_left_pos[0]) * piece.width)
            shifted_image_pos_y = int((piece.pos[1] - self.top_left_pos[1]) * piece.height)
            image.paste(piece.image, (shifted_image_pos_x, shifted_image_pos_y))
        return image

    @property
    def width(self):
        min_pos_x = min([piece.pos[0] for piece in self.pieces])
        max_pos_x = max([piece.pos[0] for piece in self.pieces])
        # Assuming pieces are regular
        return int((max_pos_x - min_pos_x + 1) * self.pieces[0].width)

    @property
    def height(self):
        min_pos_y = min([piece.pos[1] for piece in self.pieces])
        max_pos_y = max([piece.pos[1] for piece in self.pieces])
        # Assuming pieces are regular
        return int((max_pos_y - min_pos_y + 1) * self.pieces[0].height)

    @property
    def top_left_pos(self):
        min_pos_x = min([piece.pos[0] for piece in self.pieces])
        min_pos_y = min([piece.pos[1] for piece in self.pieces])
        return array([min_pos_x, min_pos_y])

    @property
    def internal_boundaries(self):
        internal_boundaries = []
        for piece in self.pieces:
            for boundary in piece.boundaries:
                if boundary.is_internal:
                    internal_boundaries.append(boundary)
        return internal_boundaries

    @property
    def external_boundaries(self):
        external_boundaries = []
        for piece in self.pieces:
            for boundary in piece.boundaries:
                if not boundary.is_internal:
                    external_boundaries.append(boundary)
        return external_boundaries

    def find_all_connections(self, other):
        valid_connections = []
        for boundary in self.external_boundaries:
            for other_boundary in other.external_boundaries:
                if not boundary.is_compatible_with(other_boundary):
                    continue
                try:
                    jigsaw_copy = deepcopy(self)
                    other_jigsaw_copy = deepcopy(other)
                    merged_boundaries = jigsaw_copy.merge_with(other_jigsaw_copy, boundary.pos, other_boundary.pos)
                    valid_connections.append(merged_boundaries)
                except InvalidJigsaw:
                    continue
        return valid_connections

    def merge_with(self, other, join_boundary_pos, other_join_boundary_pos):
        join_pos_shift = join_boundary_pos - other_join_boundary_pos

        # Translate other jigsaw's pieces:
        for piece in other.pieces:
            piece.update_pos(piece.pos + join_pos_shift)

        # Check for any overlaps:
        piece_pos_list = [tuple(piece.pos) for piece in self.pieces + other.pieces]
        piece_pos_counts = Counter(piece_pos_list)
        if max(piece_pos_counts.values()) > 1:
            raise InvalidJigsaw

        # Find merged boundaries and flag them as internal:
        merged_boundary_pairs = []
        for boundary in self.external_boundaries:
            for other_boundary in other.external_boundaries:
                if (boundary.pos == other_boundary.pos).all():
                    boundary.is_internal = True
                    other_boundary.is_internal = True

                    # TODO: Find cleaner way here
                    shifted_other_boundary = Boundary(
                        pixels=other_boundary.pixels,
                        pos=other_boundary.pos - join_pos_shift
                    )

                    merged_boundary_pairs.append((boundary, shifted_other_boundary))

        # Add other jigsaw's pieces to our jigsaw:
        self.pieces += other.pieces

        return merged_boundary_pairs


class JigsawPiece:
    def __init__(self, name, image):
        self.name = name
        self.image = image
        self._pos = array([0, 0])
        self.boundaries = self._get_boundaries()

    @property
    def pos(self):
        return self._pos

    @property
    def width(self):
        return self.image.size[0]

    @property
    def height(self):
        return self.image.size[1]

    def _get_boundaries(self):
        top_boundary = Boundary(
            pixels=[self.image.getpixel((i, 0)) for i in range(self.width)],
            pos=self._pos + array([0, -0.5])
        )
        left_boundary = Boundary(
            pixels=[self.image.getpixel((0, j)) for j in range(self.height)],
            pos=self._pos + array([-0.5, 0])
        )
        bottom_boundary = Boundary(
            pixels=[self.image.getpixel((i, self.height - 1)) for i in range(self.width)],
            pos=self._pos + array([0, 0.5])
        )
        right_boundary = Boundary(
            pixels=[self.image.getpixel((self.width - 1, j)) for j in range(self.height)],
            pos=self._pos + array([0.5, 0])
        )
        return [top_boundary, left_boundary, bottom_boundary, right_boundary]

    def update_pos(self, pos):
        for boundary in self.boundaries:
            boundary.update_pos(parent_pos=self._pos, parent_new_pos=pos)
        self._pos = pos


if __name__ == '__main__':
    for output_image in OUTPUT_ROOT.glob('*'):
        output_image.unlink()

    jigsaw_dict = get_jigsaws()
    jigsaws = jigsaw_dict['dragon_64']

    global_connection_reports = {}

    while len(jigsaws) > 1:
        for jigsaw_1, jigsaw_2 in combinations(jigsaws, 2):
            report_key = (jigsaw_1.name, jigsaw_2.name)

            if report_key in global_connection_reports:
                continue

            connection_reports = []
            for connection_group in jigsaw_1.find_all_connections(jigsaw_2):
                scores = [
                    boundary_pair[0].compare_difference_with(boundary_pair[1]) for boundary_pair in connection_group
                ]

                connection_report = {
                    'group': connection_group,
                    'score': sum(scores) / len(scores)
                }
                connection_reports.append(connection_report)

            # Determine best connection report to publish for these two jigsaws:
            global_connection_reports[report_key] = min(connection_reports, key=lambda item: item['score'])

        # Determine best connection report amongst all jigsaws:
        best_report_key = min(global_connection_reports, key=lambda key: global_connection_reports[key]['score'])

        jigsaw_1 = next(filter(lambda item: item.name == best_report_key[0], jigsaws))
        jigsaw_2 = next(filter(lambda item: item.name == best_report_key[1], jigsaws))
        connection_group = global_connection_reports[best_report_key]['group']

        # Remove reports of the jigsaws that will be merged:
        merged_keys = [
            report_key for report_key in global_connection_reports
            if report_key[0] == jigsaw_1.name or report_key[1] == jigsaw_1.name
            or report_key[0] == jigsaw_2.name or report_key[1] == jigsaw_2.name
        ]
        for merged_key in merged_keys:
            del global_connection_reports[merged_key]

        jigsaw_1.merge_with(jigsaw_2, connection_group[0][0].pos, connection_group[0][1].pos)
        jigsaw_1.image.save(OUTPUT_ROOT / f'{hash(jigsaw_1.name)}.png')
        jigsaws.remove(jigsaw_2)
        print('!')
