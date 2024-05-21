import sys
import time
import signal

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter, QColor, QPen, QPalette
from tango import AttributeProxy, DeviceProxy

# prefix for all Tango device names
TANGO_NAME_PREFIX = "epfl/station"

#add station number as arg
# definition of Tango attribute and command names
TANGO_ATTRIBUTE_LEVEL = "level"
TANGO_ATTRIBUTE_VALVE = "valve"
TANGO_ATTRIBUTE_FLOW = "flow"
TANGO_ATTRIBUTE_COLOR = "color"
TANGO_COMMAND_FILL = "Fill"
TANGO_COMMAND_FLUSH = "Flush"

NB_STATION = 6
NB_PAGE = 2


class TankWidget(QWidget):
    """
    Widget that displays the paint tank and valve
    """
    MARGIN_BOTTOM = 30
    VALVE_WIDTH = 15

    def __init__(self, tank_width, tank_height, level=0, valve=True):
        super().__init__()
        self.fill_color = QColor("grey")
        self.fill_level = level
        self.tank_height = tank_height
        self.tank_width = tank_width
        self.valve = 0
        self.flow = 0
        self.valve_text = valve
        self.setMinimumSize(self.tank_width, self.tank_height + self.MARGIN_BOTTOM)

    def setValve(self, valve):
        """
        set the valve level between 0 and 100
        """
        self.valve = valve

    def setFlow(self, flow):
        """
        set the value of the flow label
        """
        self.flow = flow

    def setColor(self, color):
        """
        set the color of the paint in hex format (e.g. #000000)
        """
        self.fill_color = QColor(color)

    def paintEvent(self, event):
        """
        paint method called to draw the UI elements
        """
        # get a painter object
        painter = QPainter(self)
        # draw tank outline as solid black line
        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        painter.drawRect(1, 1, self.width() - 2, self.height() - self.MARGIN_BOTTOM - 2)
        # draw paint color
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(self.fill_color)
        painter.drawRect(2, 2 + int((1.0 - self.fill_level) * (self.height() - self.MARGIN_BOTTOM - 4)),
                         self.width() - 4,
                         int(self.fill_level * (self.height() - self.MARGIN_BOTTOM - 4)))
        # draw valve symobl
        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        painter.drawLine(self.width() // 2, self.height() - self.MARGIN_BOTTOM, self.width() // 2,
                         self.height() - self.MARGIN_BOTTOM + 5)
        painter.drawLine(self.width() // 2, self.height(), self.width() // 2,
                         self.height() - 5)
        painter.drawLine(self.width() // 2 - self.VALVE_WIDTH, self.height() - self.MARGIN_BOTTOM + 5,
                         self.width() // 2 + self.VALVE_WIDTH,
                         self.height() - 5)
        painter.drawLine(self.width() // 2 - self.VALVE_WIDTH, self.height() - 5, self.width() // 2 + self.VALVE_WIDTH,
                         self.height() - self.MARGIN_BOTTOM + 5)
        painter.drawLine(self.width() // 2 - self.VALVE_WIDTH, self.height() - self.MARGIN_BOTTOM + 5,
                         self.width() // 2 + self.VALVE_WIDTH,
                         self.height() - self.MARGIN_BOTTOM + 5)
        painter.drawLine(self.width() // 2 - self.VALVE_WIDTH, self.height() - 5, self.width() // 2 + self.VALVE_WIDTH,
                         self.height() - 5)
        # draw labels
        if self.valve_text:
            painter.drawText(
                QRect(0, self.height() - self.MARGIN_BOTTOM, self.width() // 2 - self.VALVE_WIDTH, self.MARGIN_BOTTOM),
                Qt.AlignCenter, "%u%%" % self.valve)
            painter.drawText(
                QRect(self.width() // 2 + self.VALVE_WIDTH, self.height() - self.MARGIN_BOTTOM,
                    self.width() // 2 - self.VALVE_WIDTH, self.MARGIN_BOTTOM),
                Qt.AlignCenter, "%.1f l/s" % self.flow)


class PaintTankWidget(QWidget):
    """
    Widget to hold a single paint tank, valve slider and command buttons
    """

    def __init__(self, nbstation, name, width, height=100, fill_button=False, flush_button=False, valve_en=True,level_en=True):
        super().__init__()
        self.name = name
        self.bFi = fill_button
        self.bFl = flush_button
        self.nbstat = TANGO_NAME_PREFIX+"%s" % nbstation
        self.setGeometry(0, 0, width, height)
        self.setMinimumSize(width, height)
        self.layout = QVBoxLayout()
        self.threadpool = QThreadPool()
        self.worker = TangoBackgroundWorker(self.nbstat, self.name)
        self.worker.level.done.connect(self.setLevel)
        self.worker.flow.done.connect(self.setFlow)
        self.worker.color.done.connect(self.setColor)
        self.worker.valve.done.connect(self.setValve)
        
        
        if fill_button:
            self.buttonfi = QPushButton('Fill', self)
            self.buttonfi.setToolTip('Fill up the tank with paint')
            self.buttonfi.clicked.connect(self.on_fill)
            self.buttonfi.setStyleSheet("border : 4px solid green; border-top-left-radius : 30px ;border-bottom-left-radius : 30px ; background-color : light grey;")
            self.layout.addWidget(self.buttonfi)

        # label for level
        if level_en:
            self.label_level = QLabel("Level: --")
            self.label_level.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(self.label_level)
        

        # tank widget
        self.tank = TankWidget(width, height, valve=valve_en)
        self.layout.addWidget(self.tank, 5)

        # slider for the valve
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setFocusPolicy(Qt.NoFocus)
        self.slider.setGeometry(0, 0, width, 10)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)  # valve closed
        self.slider.setSingleStep(10)
        self.slider.setTickInterval(20)
        self.timer_slider = None
        self.slider.valueChanged[int].connect(self.changedValue)
        self.layout.addWidget(self.slider)
        
        
        if flush_button:
            self.buttonfl = QPushButton('Flush', self)
            self.buttonfl = QPushButton('Flush', self)
            self.buttonfl.setToolTip('Flush the tank')
            self.buttonfl.clicked.connect(self.on_flush)
            self.buttonfl.setStyleSheet("border : 4px solid green; border-top-left-radius : 30px ;border-bottom-left-radius : 30px ; background-color : light grey;")
            self.layout.addWidget(self.buttonfl)

        self.setLayout(self.layout)

        # set the valve attribute to fully closed
        worker = TangoWriteAttributeWorker(self.nbstat, self.name, TANGO_ATTRIBUTE_VALVE, self.slider.value() / 100.0)
        self.threadpool.start(worker)
        self.worker.start()
        # update the UI element
        self.tank.setValve(0)

    def changedValue(self):
        """
        callback when the value of the valve slider has changed
        """
        if self.timer_slider is not None:
            self.killTimer(self.timer_slider)
        # start a time that fires after 200 ms
        self.timer_slider = self.startTimer(200)

    def timerEvent(self, event):
        """
        callback when the timer has fired
        """
        self.killTimer(self.timer_slider)
        self.timer_slider = None

        # set valve attribute
        worker = TangoWriteAttributeWorker(self.nbstat, self.name, TANGO_ATTRIBUTE_VALVE, self.slider.value() / 100.0)
        worker.signal.done.connect(self.setValve)
        self.threadpool.start(worker)

    def setLevel(self, level):
        """
        set the level of the paint tank, range: 0-1
        """
        self.tank.fill_level = level
        self.label_level.setText("Level: %.1f %%" % (level * 100))
        if level > 0.95 and self.bFl:
            self.buttonfl.setStyleSheet("border : 4px solid red; border-top-left-radius : 30px ;border-bottom-left-radius : 30px ; background-color : light red;")
        else :
            if self.bFl:
                self.buttonfl.setStyleSheet("border : 4px solid green; border-top-left-radius : 30px ;border-bottom-left-radius : 30px ; background-color : light grey;")
        if level < 0.05 and self.bFi:
            self.buttonfi.setStyleSheet("border : 4px solid red; border-top-left-radius : 30px ;border-bottom-left-radius : 30px ; background-color : light red;")
        else:
            if self.bFi:
                self.buttonfi.setStyleSheet("border : 4px solid green; border-top-left-radius : 30px ;border-bottom-left-radius : 30px ; background-color : light grey;")
        self.tank.update()

    def setValve(self, valve):
        """
        set the value of the valve label
        """
        if self.timer_slider is None and not self.slider.isSliderDown():
            # user is not currently changing the slider
            self.slider.setValue(int(valve*100))
            self.tank.setValve(valve*100)

    def setFlow(self, flow):
        """
        set the value of the flow label
        """
        self.tank.setFlow(flow)

    def setColor(self, color):
        """
        set the color of the paint
        """
        self.tank.setColor(color)

    def on_fill(self):
        """
        callback method for the "Fill" button
        """
        worker = TangoRunCommandWorker(self.nbstat, self.name, TANGO_COMMAND_FILL)
        self.threadpool.start(worker)

    def on_flush(self):
        """
        callback method for the "Flush" button
        """
        worker = TangoRunCommandWorker(self.nbstat, self.name, TANGO_COMMAND_FLUSH)
        self.threadpool.start(worker)

class Color(QWidget):

    def __init__(self, color, width):
        super(Color, self).__init__()
        self.setAutoFillBackground(True)
        self.setGeometry(0, 0, width, 230)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)

class ColorMixingPlantWindow(QMainWindow):
    """
    main UI window
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Mixing Plant Simulator - EPFL CS-487")
        self.setMinimumSize(1500, 900)
 #STATION PAGE
        # Create a vertical layout
        vbox = QVBoxLayout()

        # Create a horizontal layout
        hbox = QHBoxLayout()
        hbox_title = QHBoxLayout()

	# Tools bar
        stationToolBar = QToolBar()
        fileToolBar = self.addToolBar(Qt.TopToolBarArea, stationToolBar)
        stationToolBar.setStyleSheet("QToolBar {background : #A9A9A9};")
        
	# Toolbar
		#icon button : Home
        self.button_action = QPushButton()
        self.button_action.setText("Overview")
        self.button_action.setCheckable(True)
        self.button_action.setAutoExclusive(True)
        stationToolBar.addWidget(self.button_action)
        self.button_action.setStyleSheet("border: 2px solid; border-color : #505050; background-color : #87CEEB;")
        self.button_action.clicked.connect(self.switch_home)


        stationToolBar.addSeparator()
        stationToolBar.addSeparator()
        stationToolBar.addSeparator()        
        stationToolBar.addSeparator()

		#button : toolButton_1
        self.toolButton_1 = QPushButton()
        self.toolButton_1.setText("Station 1 ")
        self.toolButton_1.setCheckable(True)
        self.toolButton_1.setAutoExclusive(True)
        self.toolButton_1.clicked.connect(self.switch_station1)
        stationToolBar.addWidget(self.toolButton_1)
        self.toolButton_1.setStyleSheet("border: 2px solid; border-color : #505050; background-color : #87CEEB;")

        stationToolBar.addSeparator()
        stationToolBar.addSeparator()
        stationToolBar.addSeparator()

		#button : toolButton_2
        self.toolButton_2 = QPushButton()
        self.toolButton_2.setText("Station 2 ")
        self.toolButton_2.setCheckable(True)
        self.toolButton_2.setAutoExclusive(True)
        self.toolButton_2.clicked.connect(self.switch_station2)
        stationToolBar.addWidget(self.toolButton_2)
        self.toolButton_2.setStyleSheet("border: 2px solid; border-color : #505050; background-color : #87CEEB;")

        stationToolBar.addSeparator()
        stationToolBar.addSeparator()
        stationToolBar.addSeparator()

		#button : toolButton_3
        self.toolButton_3 = QPushButton()
        self.toolButton_3.setText("Station 3 ")
        self.toolButton_3.setCheckable(True)
        self.toolButton_3.setAutoExclusive(True)
        self.toolButton_3.clicked.connect(self.switch_station3)
        stationToolBar.addWidget(self.toolButton_3)
        self.toolButton_3.setStyleSheet("border: 2px solid; border-color : #505050; background-color : #87CEEB;")

        stationToolBar.addSeparator()
        stationToolBar.addSeparator()
        stationToolBar.addSeparator()

		#button : toolButton_4
        self.toolButton_4 = QPushButton()
        self.toolButton_4.setText("Station 4 ")
        self.toolButton_4.setCheckable(True)
        self.toolButton_4.setAutoExclusive(True)
        self.toolButton_4.clicked.connect(self.switch_station4)
        stationToolBar.addWidget(self.toolButton_4)
        self.toolButton_4.setStyleSheet("border: 2px solid; border-color : #505050; background-color : #87CEEB;")

        stationToolBar.addSeparator()
        stationToolBar.addSeparator()
        stationToolBar.addSeparator()

		#button : toolButton_5
        self.toolButton_5 = QPushButton()
        self.toolButton_5.setText("Station 5 ")
        self.toolButton_5.setCheckable(True)
        self.toolButton_5.setAutoExclusive(True)
        self.toolButton_5.clicked.connect(self.switch_station5)
        stationToolBar.addWidget(self.toolButton_5)
        self.toolButton_5.setStyleSheet("border: 2px solid; border-color : #505050; background-color : #87CEEB;")

        stationToolBar.addSeparator()
        stationToolBar.addSeparator()
        stationToolBar.addSeparator()

		#button : toolButton_6
        self.toolButton_6 = QPushButton()
        self.toolButton_6.setText("Station 6 ")
        self.toolButton_6.setCheckable(True)
        self.toolButton_6.setAutoExclusive(True)
        self.toolButton_6.clicked.connect(self.switch_station6)
        stationToolBar.addWidget(self.toolButton_6)
        self.toolButton_6.setStyleSheet("border: 2px solid; border-color : #505050; background-color : #87CEEB;")


	# Central part
        self.window = QWidget()
        self.setCentralWidget(self.window)
		
	
		#title
        self.title_station = QLabel()
        self.title_station.resize(100,100)
        self.title_station.setText("GENERAL OVERVIEW")
        self.title_station.setAlignment(Qt.AlignCenter)
        self.title_station.setStyleSheet("QLabel {background : #C9944C};")

		

		#hbox
        
        hbox_title.addWidget(self.title_station)
        vbox.addLayout(hbox_title)

        self.nbstation = 0
        self.station_layout = QStackedLayout()

        for nbstation in range(1, NB_STATION+1):
            widget = QWidget()

            test = QVBoxLayout(widget)

            hbox = QHBoxLayout()
            hbox.addWidget(PaintTankWidget(nbstation, "cyan", height=200, width=150, fill_button=True))
            hbox.addWidget(PaintTankWidget(nbstation, "magenta", width=150, fill_button=True))
            hbox.addWidget(PaintTankWidget(nbstation, "yellow", width=150, fill_button=True))
            hbox.addWidget(PaintTankWidget(nbstation, "black", width=150, fill_button=True))
            hbox.addWidget(PaintTankWidget(nbstation, "white", width=150, fill_button=True))

            test.addLayout(hbox)
            hbox = QHBoxLayout()
            hbox.addWidget(PaintTankWidget(nbstation, "mixer", width=600, flush_button=True))
            hbox.addWidget(Color('red',width = 200))
            test.addLayout(hbox)
            self.station_layout.addWidget(widget)

        self.station_layout.setCurrentIndex(self.nbstation)


	#Tables
		#Alarm
        self.table_layout = QHBoxLayout()
        self.table_layout_alarm = QHBoxLayout()
        self.table_layout_event = QHBoxLayout()
        self.alarm_layout = QVBoxLayout()
        title_alarm = QLabel("Alarms")
        title_alarm.setAlignment(Qt.AlignCenter)
        title_alarm.setStyleSheet("border: 3px solid; border-color : #DC143C; background-color : #DC143C;")
        self.alarm_layout.addWidget(title_alarm)
        self.alarm_table = QTableWidget(30, 4)
        self.alarm_layout.addWidget(self.alarm_table)


        self.alarm_table.verticalHeader().hide()
        self.alarm_table.horizontalHeader().hide()
        self.alarm_table.horizontalHeader().setStretchLastSection(True)

        self.alarm_layout_copy = QVBoxLayout()
        title_alarm = QLabel("Alarms")
        title_alarm.setAlignment(Qt.AlignCenter)
        title_alarm.setStyleSheet("border: 3px solid; border-color : #DC143C; background-color : #DC143C;")
        self.alarm_layout_copy.addWidget(title_alarm)
        self.alarm_table = QTableWidget(30, 4)
        self.alarm_layout_copy.addWidget(self.alarm_table)


        self.alarm_table.verticalHeader().hide()
        self.alarm_table.horizontalHeader().hide()
        self.alarm_table.horizontalHeader().setStretchLastSection(True)

		#Events
			#filter
        self.filter = QComboBox(self)
        self.filter.setEditable(True)
        self.list_filter_event = ["None", "color tank filling","color tank full", "station start", "station pause","station stop", "recipe begin","recipe end","mix tank filling","mix tank full", "mix tank mixing", "mix tank emptying", "mix tank empty"]
        self.list_filter_alarm = [""]
        self.filter.addItems(self.list_filter_event+self.list_filter_alarm)
        self.filter.setStyleSheet("border: 1px solid; border-color : #808080; background-color : #798081;")
        self.line_edit_filter = self.filter.lineEdit()
        self.line_edit_filter.setAlignment(Qt.AlignCenter)
        self.line_edit_filter.setReadOnly(True)
        self.line_edit_filter.setStyleSheet("border: 1px solid; border-color : #808080; background-color : white;")
        #self.filter.activated[str].connect(self.filter_change)
        height_filter = 23
        width_filter = 150
        self.filter.setGeometry(0, 0, width_filter, height_filter)
        self.filter.setMinimumSize(width_filter, height_filter)
        self.filter.setMaximumSize(width_filter, height_filter)


        self.event_layout = QVBoxLayout()
        filter_layout = QHBoxLayout()
        title_alarm_event = QLabel("Events & Alarms")
        title_alarm_event.setAlignment(Qt.AlignCenter)
        title_alarm_event.setStyleSheet("border: 3px solid; border-color : #808080; background-color : #798081;")
        filter_layout.addWidget(title_alarm_event)
        filter_layout.addWidget(self.filter)
        self.event_layout.addLayout(filter_layout)
        self.event_table = QTableWidget(30, 4)
        self.event_layout.addWidget(self.event_table)
        self.event_table.verticalHeader().hide()
        self.event_table.horizontalHeader().hide()
        self.event_table.horizontalHeader().setStretchLastSection(True)

        self.event_layout_copy = QVBoxLayout()
        filter_layout = QHBoxLayout()
        title_alarm_event = QLabel("Events & Alarms")
        title_alarm_event.setAlignment(Qt.AlignCenter)
        title_alarm_event.setStyleSheet("border: 3px solid; border-color : #808080; background-color : #798081;")
        filter_layout.addWidget(title_alarm_event)
        filter_layout.addWidget(self.filter)
        self.event_layout_copy.addLayout(filter_layout)
        self.event_table = QTableWidget(30, 4)
        self.event_layout_copy.addWidget(self.event_table)
        
        self.event_table.verticalHeader().hide()
        self.event_table.horizontalHeader().hide()
        self.event_table.horizontalHeader().setStretchLastSection(True)

		#Layout
        self.table_layout_alarm.addLayout(self.alarm_layout_copy)
        self.table_layout_event.addLayout(self.event_layout_copy)
        self.table_layout.addLayout(self.alarm_layout)
        self.table_layout.addLayout(self.event_layout)



#HOME PAGE

        #Box
        self.vbox_home = QVBoxLayout()
        hbox_1 = QHBoxLayout()
        hbox_2 = QHBoxLayout()
        self.vbox_station_1 =QVBoxLayout()
        self.vbox_station_2 =QVBoxLayout()
        self.vbox_station_3 =QVBoxLayout()
        self.vbox_station_4 =QVBoxLayout()
        self.vbox_station_5 =QVBoxLayout()
        self.vbox_station_6 =QVBoxLayout()

        
        #fill the box
	
		#Name station
        title_home_station_1 = QLabel()
        title_home_station_1.setText("Station 1")
        title_home_station_1.setAlignment(Qt.AlignCenter)
        title_home_station_1.setStyleSheet("border : 2px solid; border-color : #8682B4; background-color : #87CEEB;")

        title_home_station_2 = QLabel()
        title_home_station_2.setText("Station 2")
        title_home_station_2.setAlignment(Qt.AlignCenter)
        title_home_station_2.setStyleSheet("border : 2px solid; border-color : #8682B4; background-color : #87CEEB;")

        title_home_station_3 = QLabel()
        title_home_station_3.setText("Station 3")
        title_home_station_3.setAlignment(Qt.AlignCenter)
        title_home_station_3.setStyleSheet("border : 2px solid; border-color : #8682B4; background-color : #87CEEB;")

        title_home_station_4 = QLabel()
        title_home_station_4.setText("Station 4")
        title_home_station_4.setAlignment(Qt.AlignCenter)
        title_home_station_4.setStyleSheet("border : 2px solid; border-color : #8682B4; background-color : #87CEEB;")

        title_home_station_5 = QLabel()
        title_home_station_5.setText("Station 5")
        title_home_station_5.setAlignment(Qt.AlignCenter)
        title_home_station_5.setStyleSheet("border : 2px solid; border-color : #8682B4; background-color : #87CEEB;")


        title_home_station_6 = QLabel()
        title_home_station_6.setText("Station 6")
        title_home_station_6.setAlignment(Qt.AlignCenter)
        title_home_station_6.setStyleSheet("border : 2px solid; border-color : #8682B4; background-color : #87CEEB;")

        height_station = 75
        width_station = 435

        title_home_station_1.setGeometry(0, 0, width_station, height_station)
        title_home_station_1.setMinimumSize(width_station, height_station)
        title_home_station_1.setMaximumSize(width_station, height_station)

        title_home_station_2.setGeometry(0, 0, width_station, height_station)
        title_home_station_2.setMinimumSize(width_station, height_station)
        title_home_station_2.setMaximumSize(width_station, height_station)

        title_home_station_3.setGeometry(0, 0, width_station, height_station)
        title_home_station_3.setMinimumSize(width_station, height_station)
        title_home_station_3.setMaximumSize(width_station, height_station)

        title_home_station_4.setGeometry(0, 0, width_station, height_station)
        title_home_station_4.setMinimumSize(width_station, height_station)
        title_home_station_4.setMaximumSize(width_station, height_station)

        title_home_station_5.setGeometry(0, 0, width_station, height_station)
        title_home_station_5.setMinimumSize(width_station, height_station)
        title_home_station_5.setMaximumSize(width_station, height_station)

        title_home_station_6.setGeometry(0, 0, width_station, height_station)
        title_home_station_6.setMinimumSize(width_station, height_station)
        title_home_station_6.setMaximumSize(width_station, height_station)

		

       

		#Table events & alarms for station

        event_layout_1 = QVBoxLayout()
        title_alarm_event = QLabel("Events & Alarms 1")
        title_alarm_event.setAlignment(Qt.AlignCenter)
        title_alarm_event.setStyleSheet("border: 3px solid; border-color : #808080; background-color : #798081;")
        event_layout_1.addWidget(title_alarm_event)
        self.event_table_1 = QTableWidget(20, 4)
        event_layout_1.addWidget(self.event_table_1)
        
        self.event_table_1.verticalHeader().hide()
        self.event_table_1.horizontalHeader().hide()
        self.event_table_1.horizontalHeader().setStretchLastSection(True)

        event_layout_2 = QVBoxLayout()
        title_alarm_event = QLabel("Events & Alarms 2")
        title_alarm_event.setAlignment(Qt.AlignCenter)
        title_alarm_event.setStyleSheet("border: 3px solid; border-color : #808080; background-color : #798081;")
        event_layout_2.addWidget(title_alarm_event)
        self.event_table_2 = QTableWidget(20, 4)
        event_layout_2.addWidget(self.event_table_2)
        
        self.event_table_2.verticalHeader().hide()
        self.event_table_2.horizontalHeader().hide()
        self.event_table_2.horizontalHeader().setStretchLastSection(True)

        event_layout_3 = QVBoxLayout()
        title_alarm_event = QLabel("Events & Alarms 3")
        title_alarm_event.setAlignment(Qt.AlignCenter)
        title_alarm_event.setStyleSheet("border: 3px solid; border-color : #808080; background-color : #798081;")
        event_layout_3.addWidget(title_alarm_event)
        self.event_table_3 = QTableWidget(20, 4)
        event_layout_3.addWidget(self.event_table_3)
        
        self.event_table_3.verticalHeader().hide()
        self.event_table_3.horizontalHeader().hide()
        self.event_table_3.horizontalHeader().setStretchLastSection(True)

        event_layout_4 = QVBoxLayout()
        title_alarm_event = QLabel("Events & Alarms 4")
        title_alarm_event.setAlignment(Qt.AlignCenter)
        title_alarm_event.setStyleSheet("border: 3px solid; border-color : #808080; background-color : #798081;")
        event_layout_4.addWidget(title_alarm_event)
        self.event_table_4 = QTableWidget(20, 4)
        event_layout_4.addWidget(self.event_table_4)
        
        self.event_table_4.verticalHeader().hide()
        self.event_table_4.horizontalHeader().hide()
        self.event_table_4.horizontalHeader().setStretchLastSection(True)

        event_layout_5 = QVBoxLayout()
        title_alarm_event = QLabel("Events & Alarms 5")
        title_alarm_event.setAlignment(Qt.AlignCenter)
        title_alarm_event.setStyleSheet("border: 3px solid; border-color : #808080; background-color : #798081;")
        event_layout_5.addWidget(title_alarm_event)
        self.event_table_5 = QTableWidget(20, 4)
        event_layout_5.addWidget(self.event_table_5)
        
        self.event_table_5.verticalHeader().hide()
        self.event_table_5.horizontalHeader().hide()
        self.event_table_5.horizontalHeader().setStretchLastSection(True)


        event_layout_6 = QVBoxLayout()
        title_alarm_event = QLabel("Events & Alarms 6")
        title_alarm_event.setAlignment(Qt.AlignCenter)
        title_alarm_event.setStyleSheet("border: 3px solid; border-color : #808080; background-color : #798081;")
        event_layout_6.addWidget(title_alarm_event)
        self.event_table_6 = QTableWidget(20, 4)
        event_layout_6.addWidget(self.event_table_6)
        
        self.event_table_6.verticalHeader().hide()
        self.event_table_6.horizontalHeader().hide()
        self.event_table_6.horizontalHeader().setStretchLastSection(True)


		#include widget in the vbox
        self.vbox_station_1.addWidget(title_home_station_1)
        self.vbox_station_2.addWidget(title_home_station_2)
        self.vbox_station_3.addWidget(title_home_station_3)
        self.vbox_station_4.addWidget(title_home_station_4)
        self.vbox_station_5.addWidget(title_home_station_5)
        self.vbox_station_6.addWidget(title_home_station_6)

        
        
        self.vbox_station_1.addLayout(event_layout_1)
        self.vbox_station_2.addLayout(event_layout_2)
        self.vbox_station_3.addLayout(event_layout_3)
        self.vbox_station_4.addLayout(event_layout_4)
        self.vbox_station_5.addLayout(event_layout_5)
        self.vbox_station_6.addLayout(event_layout_6)
        
#Include Box

        hline = QFrame()
        hline.setFrameShape(QFrame.HLine);
        hline.setStyleSheet("border: 3px solid; border-color : black;")
        vline1 = QFrame()
        vline1.setFrameShape(QFrame.VLine);
        vline1.setStyleSheet("border: 3px solid; border-color : black;")
        vline2 = QFrame()
        vline2.setFrameShape(QFrame.VLine);
        vline2.setStyleSheet("border: 3px solid; border-color : black;")
        vline3 = QFrame()
        vline3.setFrameShape(QFrame.VLine);
        vline3.setStyleSheet("border: 3px solid; border-color : black;")
        vline4 = QFrame()
        vline4.setFrameShape(QFrame.VLine);
        vline4.setStyleSheet("border: 3px solid; border-color : black;")

        self.vbox_home.addLayout(hbox_1)
        self.vbox_home.addWidget(hline)
        self.vbox_home.addLayout(hbox_2)

        hbox_1.addLayout(self.vbox_station_1)
        hbox_1.addWidget(vline1)
        hbox_1.addLayout(self.vbox_station_2)
        hbox_1.addWidget(vline2)
        hbox_1.addLayout(self.vbox_station_3)

        hbox_2.addLayout(self.vbox_station_4)
        hbox_2.addWidget(vline3)
        hbox_2.addLayout(self.vbox_station_5)
        hbox_2.addWidget(vline4)
        hbox_2.addLayout(self.vbox_station_6)
	
#PAGES
        vbox_page_alarm_event_table = QVBoxLayout()
        self.num_page = 0
        self.page_layout = QStackedLayout()
        

        for page in range(NB_PAGE):
            widget = QWidget()

            test = QVBoxLayout(widget)

            if page == 0 :
                hbox = QHBoxLayout()
                hbox.addLayout(self.vbox_home)
                test.addLayout(hbox)
            if page == 1 :
                vbox_page_alarm_event_table.addLayout(self.station_layout)
                vbox_page_alarm_event_table.addLayout(self.table_layout)
                test.addLayout(vbox_page_alarm_event_table)
            if page == 2 :
                test.addLayout(self.table_layout_alarm)
            if page == 3 :
                test.addLayout(self.table_layout_event)
            self.page_layout.addWidget(widget)

        self.page_layout.setCurrentIndex(self.num_page)

        vbox.addLayout(self.page_layout)       

        self.window.setLayout(vbox)

	
    def _createMenuBar(self):
        menuBar = QMenuBar(self)
        # Creating menus using a QMenu object
        fileMenu = QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        # Creating menus using a title
        editMenu = menuBar.addMenu("&Edit")
        helpMenu = menuBar.addMenu("&Help")

    def set_station(self, number):
        self.num_page=1
        self.page_layout.setCurrentIndex(self.num_page)

        self.nbstation = number
        self.station_layout.setCurrentIndex(self.nbstation)

        self.update_title()
        
    
    def update_title(self):
        if self.num_page==0:
            self.title_station.setText(f"GENERAL OVERVIEW")
        if self.num_page==1:
            self.title_station.setText(f"MIXING PLANT --- <b>Station {self.nbstation+1}</b>")

    
    
    
    @pyqtSlot()
    def switch_station1(self):
        self.set_station(0)
    
    @pyqtSlot()
    def switch_station2(self):
        self.set_station(1)

    @pyqtSlot()
    def switch_station3(self):
        self.set_station(2)

    @pyqtSlot()
    def switch_station4(self):
        self.set_station(3)
        
    @pyqtSlot()
    def switch_station5(self):
        self.set_station(4)
    
    @pyqtSlot()
    def switch_station6(self):
        self.set_station(5)
    @pyqtSlot()
    def switch_home(self):
        self.num_page=0
        self.page_layout.setCurrentIndex(self.num_page)
        self.update_title()    


class WorkerSignal(QObject):
    """
    Implementation of a QT signal
    """
    done = pyqtSignal(object)


class TangoWriteAttributeWorker(QRunnable):
    """
    Worker class to write to a Tango attribute in the background.
    This is used to avoid blocking the main UI thread.
    """

    def __init__(self, name, device, attribute, value):
        super().__init__()
        self.signal = WorkerSignal()
        self.path = "%s/%s/%s" % (name, device, attribute)
        self.value = value

    @pyqtSlot()
    def run(self):
        """
        main method of the worker
        """
        print("setDeviceAttribute: %s = %f" % (self.path, self.value))
        attr = AttributeProxy(self.path)
        try:
            # write attribute
            attr.write(self.value)
            # read back attribute
            data = attr.read()
            # send callback signal to UI
            self.signal.done.emit(data.value)
        except Exception as e:
            print("Failed to write to the Attribute: %s. Is the Device Server running?" % self.path)


class TangoRunCommandWorker(QRunnable):
    """
    Worker class to call a Tango command in the background.
    This is used to avoid blocking the main UI thread.
    """

    def __init__(self, name, device, command, *args):
        """
        creates a new instance for the given device instance and command
        :param device: device name
        :param command: name of the command
        :param args: command arguments
        """
        super().__init__()
        self.signal = WorkerSignal()
        self.device = "%s/%s" % (name, device)
        self.command = command
        self.args = args

    @pyqtSlot()
    def run(self):
        """
        main method of the worker
        """
        print("device: %s command: %s args: %s" % (self.device, self.command, self.args))
        try:
            device = DeviceProxy(self.device)
            # get device server method
            func = getattr(device, self.command)
            # call command
            result = func(*self.args)
            # send callback signal to UI
            self.signal.done.emit(result)
        except Exception as e:
            print("Error calling device server command: device: %s command: %s" % (self.device, self.command))


class TangoBackgroundWorker(QThread):
    """
    This worker runs in the background and polls certain Tango device attributes (e.g. level, flow, color).
    It will signal to the UI when new data is available.
    """

    def __init__(self, name, device, interval =0.5):
        """
        creates a new instance
        :param name: station name
        :param device: device name
        :param interval: polling interval in seconds
        """
        super().__init__()
        self.name = name
        self.device= device
        self.interval = interval
        self.level = WorkerSignal()
        self.flow = WorkerSignal()
        self.color = WorkerSignal()
        self.valve = WorkerSignal()

    def run(self):
        """
        main method of the worker
        """
        print("Starting TangoBackgroundWorker for '%s' tank" % self.name)
        # define attributes
        try:
            level = AttributeProxy("%s/%s/%s" % (self.name, self.device, TANGO_ATTRIBUTE_LEVEL))
            flow = AttributeProxy("%s/%s/%s" % (self.name, self.device, TANGO_ATTRIBUTE_FLOW))
            color = AttributeProxy("%s/%s/%s" % (self.name, self.device, TANGO_ATTRIBUTE_COLOR))
            valve = AttributeProxy("%s/%s/%s" % (self.name, self.device, TANGO_ATTRIBUTE_VALVE))
        except Exception as e:
            print("Error creating AttributeProxy for %s" % self.device)
            return

        while True:
            try:
                # read attributes
                data_color = color.read()
                data_level = level.read()
                data_flow = flow.read()
                data_valve = valve.read()
                # signal to UI
                self.color.done.emit(data_color.value)
                self.level.done.emit(data_level.value)
                self.flow.done.emit(data_flow.value)
                self.valve.done.emit(data_valve.value)
            except Exception as e:
                print("Error reading from the device: %s" % e)

            # wait for next round
            time.sleep(self.interval)


if __name__ == '__main__':
    # register signal handler for CTRL-C events
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # init the QT application and the main window
    app = QApplication(sys.argv)
    ui = ColorMixingPlantWindow()
    # show the UI
    ui.show()
    # start the QT application (blocking until UI exits)
    app.exec_()
