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


def get_jigsaws():
    jigsaws_dict = {}
    for jigsaw_path in JIGSAWS_ROOT.glob('*'):
        jigsaws_dict[jigsaw_path.name] = []
        for jigsaw_piece_path in jigsaw_path.glob('*'):
            jigsaw_piece_image = Image.open(jigsaw_piece_path)

            jigsaw_piece = JigsawPiece(
                name=jigsaw_piece_path.name,
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

    def join_new_piece(self, new_piece):
        pass

    def find_all_valid_connections(self, other):
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
    jigsaw_dict = get_jigsaws()
    jigsaws = jigsaw_dict['dragon_16']

    while len(jigsaws) > 1:
        global_valid_connection_groups = []
        global_scores = []

        for jigsaw_1, jigsaw_2 in combinations(jigsaws, 2):
            print(jigsaw_1.name, jigsaw_2.name, len(jigsaw_1.find_all_valid_connections(jigsaw_2)))
            valid_connection_groups = jigsaw_1.find_all_valid_connections(jigsaw_2)
            for valid_connection_group in valid_connection_groups:
                global_valid_connection_groups.append((jigsaw_1, jigsaw_2, valid_connection_group))
                global_scores.append(sum(
                    [boundary_pair[0].compare_difference_with(boundary_pair[1]) for boundary_pair in
                     valid_connection_group]) / len(valid_connection_group))

        print(global_valid_connection_groups)
        print(global_scores)
        index = global_scores.index(min(global_scores))
        print(index)

        jigsaw_1, jigsaw_2, valid_connection_group = global_valid_connection_groups[index]
        jigsaw_1.merge_with(jigsaw_2, valid_connection_group[0][0].pos, valid_connection_group[0][1].pos)
        jigsaws.remove(jigsaw_2)
        pass

    print('!')

    #         for name_1, boundary_1 in jigsaw_piece_1._boundaries.items():
    #             for name_2, boundary_2 in jigsaw_piece_2._boundaries.items():
    #                 error = compare_boundaries(boundary_1, boundary_2)
    #                 if error != -1:
    #                     report = jigsaw_piece_1.name, name_1, jigsaw_piece_2.name, name_2, error
    #                     reports.append(report)
    #
    # reports.sort(key=lambda e: e[-1])
    # print(*reports, sep='\n')
