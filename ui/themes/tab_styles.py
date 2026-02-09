"""Shared tab bar styling - Single source of truth for tab appearance.

This file defines the tab bar styles used throughout the application.
Edit once here, changes apply everywhere!
"""

TAB_BAR_STYLESHEET = """
QTabBar {
    background-color: #2b2b2b;
    border: none;
}

QTabBar::tab {
    background-color: #2D2D2D;
    color: #AAAAAA;
    padding: 0px 5px 0px 20px; 
    margin-right: 2px;
    margin-bottom: 0px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
    min-height: 30px;
    border: none;
    position: relative; /* close button absolute için şart */
}

QTabBar::tab:selected {
    background-color: #1E1E1E;
    color: #FFFFFF;
    font-weight: bold;
    padding: 0px 5px 0px 20px;
    margin-bottom: 0px;
    border-bottom: 4px solid #0078d4;
}

QTabBar::close-button {
    margin: 0px;
    padding: 0px;
    width: 16px;
    height: 16px;
    position: absolute;
    right: 6px; 
    top: 4px;        /* Hizalama buradan */
}

"""

TAB_WIDGET_STYLESHEET = """
QTabWidget {
    border: none;
    padding: 0px;
    margin: 0px;
}

QTabWidget::pane {
    border: none;
    background: transparent;
    background-color: #1E1E1E;
    position: absolute;
    padding: 0px;
    margin: 0px;
    margin-top: -4px;
    top: 0px;
}
"""

