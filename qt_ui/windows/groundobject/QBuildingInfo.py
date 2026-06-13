import os

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout

from game.config import REWARDS
from game.theater import Player, TheaterUnit


class QBuildingInfo(QGroupBox):
    def __init__(self, building: TheaterUnit, ground_object, viewer: Player):
        super(QBuildingInfo, self).__init__()
        self.building = building
        self.ground_object = ground_object
        self.viewer = viewer
        self.init_ui()

    def init_ui(self):
        self.header = QLabel()
        path = os.path.join(
            "./resources/ui/units/buildings/" + self.building.icon + ".png"
        )
        visible_alive = self.building.alive_for_player(self.viewer)
        if not visible_alive:
            pixmap = QPixmap("./resources/ui/units/buildings/dead.png")
        elif os.path.isfile(path):
            pixmap = QPixmap(path)
        else:
            pixmap = QPixmap("./resources/ui/units/buildings/missing.png")
        self.header.setPixmap(pixmap)
        self.name = QLabel(self.building.short_name_for(self.viewer))
        self.name.setProperty("style", "small")
        layout = QVBoxLayout()
        layout.addWidget(self.header)
        layout.addWidget(self.name)

        if self.ground_object.category in REWARDS:
            income_label_text = (
                "Value: " + str(REWARDS[self.ground_object.category]) + "M"
            )
            if not visible_alive:
                income_label_text = "<s>" + income_label_text + "</s>"
            self.reward = QLabel(income_label_text)
            layout.addWidget(self.reward)

        footer = QHBoxLayout()
        self.setLayout(layout)
