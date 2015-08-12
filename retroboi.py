#!/usr/bin/env python
# encoding: utf-8

'''

RetroBoi is a simple lightweight python interface for retropi like projects.

DEPENDENCIES

* npyscreen==4.9.1

INSTALL

I suggest using a virtual environment.

#> sudo apt-get install python-virtualenv
#> virtualenv ~/py27
#> . ~/py27/bin/activate
#> pip install npyscreen
#> cp retroboi.py retroboi.sh ~/

CONFIGURING

1. Set the `romdir` variable
2. Add a default.cfg in each "system" directory within the romdir. e.g.
    `romdir`/snes/default.cfg

[default]
filter = .bin .BIN .zip .ZIP
command = /usr/bin/retroarch -L /path/to/libretro.core -c /path/to/global.conf
    --appendconfig /path/to/megadrive.cfg %s

%s is passed the rom path and filename (sh_escaped)

command can be anything, I prefer to use runcommand.sh commands here.
see emulationstation/es_systems.cfg and just copy the filter and command
from there, change `%ROM$`` for %s, and bob's ur uncle.

STARTUP

add the retroboi.sh as the executable to call instead of emulationstation in
either /etc/profile or bashrc, depending on what you are using.

CONTROLS IMPLEMENTED

"a" button selects a game
"i" button changes system
"-" quits
"+" reloads
arrow keys nav up and down

rom codes

'''

import os
import subprocess
import logging
import ConfigParser
import npyscreen, curses

# variables

# top level romdir with SYSTEM subdirs
romdir = 'roms'

try:
    logging.basicConfig(filename='%s/retroboi.log' % romdir,level=logging.DEBUG)
except Exception, e:
    print("Unable to open logfile, disabling logging")
    pass

# button mappings for interface ( arrow keys for nav assumed )
a_button = "a"
b_button = "b"
select_button = "o"
start_button = "p"
escape_button = "-"
reload_button = "+"
# menu_button = "KEY_F(1)"

# the config file name to look for per SYSTEM romdir
system_config_file = "default.cfg"
terminal_width = 53
terminal_height = 20

# State vars
# place to store callback functions
cb = {}
systems = []

# main app class
class RetroBoiApp(npyscreen.NPSAppManaged):
    name = "Main"
    def onStart(self):
        logging.debug("starting RetroBoiApp")
        for system in systems:
            logging.debug("adding form for system: %s" % system)
            self.addForm(system.upper(), MainForm, name=system, lines=terminal_height, columns=terminal_width,  minimum_lines=terminal_height, minimum_columns=terminal_width)

    def change_form(self, name):
        logging.debug("switching to system %s" % name)
        self.switchForm(name)
        self.resetHistory()

    def onCleanExit(self):
        npyscreen.notify_wait("Goodbye!")


class MainForm(npyscreen.FormMultiPage):

    def create(self):
        # load system config
        logging.debug("requesting system config for %s" % self.name)
        self.config = getSystemConfig(self.name)
        #self.page = 0
        # The menus are created here.
        # self.m1 = self.add_menu(name="Main Menu", shortcut="^M")
        # self.m1.addItemsFromList([
        #     ("Shutdown", self.shutdown, None, None, ("some text",)),
        #     ("Reboot",   self.reboot, "e"),
        #     ("Exit Application", self.exit_application, "é"),
        # ])

        if self.config.has_section("default"):
            logging.debug("adding %s roms to UI" % self.name)

            item_count_max = terminal_height - 4
            item_count = 0

            for rom in getSystemRoms(self.name, self.config):
                # setup the callback function with the command
                cb[rom] = runGame(self.config.get('default', 'command') % sh_escape(getSystemRomDir(self.name) + "/" + rom))

                self.add(RomButtonPress, name=rom[:terminal_width-13], when_pressed_function=cb[rom], color='WHITE')
                item_count = item_count + 1
                if item_count >= item_count_max:
                    item_count=0
                    self.add_page()

                # TODO FIXME when inteligence available in MultiPageWithMenus
                #self.add_widget_intelligent(RomButtonPress, name=rom[:terminal_width-13], when_pressed_function=cb[rom], color='WHITE')

        # input handler
        logging.debug("binding %s to system_select" % select_button)
        self.add_handlers({select_button: self.change_forms})
        self.add_handlers({escape_button: self.exit_application})
        self.add_handlers({reload_button: reload})
        # self.add_handlers({curses.KEY_NPAGE: self.page_down})

        # self.handlers = {
        #     curses.ascii.NL:   self.h_exit_down,
        #     curses.ascii.CR:   self.h_exit_down,
        #     curses.ascii.TAB:  self.h_exit_down,
        #     curses.KEY_DOWN:   self.h_exit_down,
        #     curses.KEY_UP:     self.h_exit_up,
        #     # curses.KEY_LEFT:   self.page_up,
        #     # curses.KEY_RIGHT:  self.page_down,
        #     curses.ascii.ESC:  self.h_exit_escape,
        #     curses.KEY_MOUSE:  self.h_exit_mouse,
        #     select_button:     self.change_forms,
        #     escape_button:     self.exit_application,
        #     reload_button:     reload,
        #     # curses.KEY_NPAGE:  self.page_down
        # }

    def on_ok(self):
        # Exit the application if the OK button is pressed.
        self.parentApp.switchForm(None)

    def change_forms(self, *args, **keywords):
        if systems.index(self.name) < len(systems)-1:
            change_to = systems[systems.index(self.name)+1].upper()
            logging.debug("setting system to %s" % change_to)
        else:
            change_to = systems[0].upper()
            logging.debug("setting system to %s" % change_to)

        self.parentApp.change_form(change_to)

    # def page_down(self, *args, **kwargs):
    #     self.page = self.page+1
    #     try:
    #         self.switch_page(self.page)
    #     except:
    #         self.page=0
    #         self.switch_page(self.page)
    #
    # def page_up(self, *args, **kwargs):
    #     if self.page > 0:
    #         self.page = self.page-1
    #         try:
    #             self.switch_page(self.page)
    #         except:
    #             self.page=0
    #             self.switch_page(self.page)

    def shutdown(self):
        logging.debug("shutdown")
        curses.beep()

    def reboot(self):
        logging.debug("reboot")
        curses.beep()

    def exit_application(self, *args, **kwargs):
        logging.debug("quit")
        curses.beep()
        self.parentApp.setNextForm(None)
        self.editing = False
        self.parentApp.switchFormNow()


class RomButtonPress(npyscreen.wgbutton.MiniButton):

    def __init__(self, screen, when_pressed_function=None, *args, **keywords):
        super(RomButtonPress, self).__init__(screen, *args, **keywords)
        self.when_pressed_function = when_pressed_function

    def set_up_handlers(self):
        super(RomButtonPress, self).set_up_handlers()

        self.handlers.update({
                curses.ascii.NL: self.h_toggle,
                curses.ascii.CR: self.h_toggle,
                a_button: self.h_toggle,
            })

    def destroy(self):
        self.when_pressed_function = None
        del self.when_pressed_function

    def h_toggle(self, ch):
        self.value = True
        self.display()
        if self.when_pressed_function:
            self.when_pressed_function()
        else:
            self.whenPressed()
        self.value = False
        self.display()

    def whenPressed(self):
        pass



"""
return the roms in the SYSTEM directory
"""
def getSystemRoms(name, config):
    roms = []
    filter = tuple(config.get("default", "filter").split(" "))
    logging.debug("filter %s" % str(filter))
    tmpdir = "%s/%s" % (romdir, name)
    logging.debug("searching for roms in %s" % tmpdir)
    for dirname, dirnames, filenames in os.walk(tmpdir):
        for f in sorted(filenames):
            if f.endswith(filter):
                logging.debug("found rom: %s" % f)
                roms.append(f)
            else:
                logging.debug("ignoring %s" % f)
        break
    logging.debug("returning roms list %s" % roms)
    return roms

"""
return the full path to the SYSTEM
"""
def getSystemRomDir(name):
    tmpdir = "%s/%s" % (romdir, name)
    return tmpdir

"""
return a instance of ConfigParser with the config populated
"""
def getSystemConfig(name):
    tmpdir = "%s/%s/%s" % (romdir, name, system_config_file)
    logging.debug("getting config file: %s" % tmpdir)
    config = ConfigParser.ConfigParser()
    config.read(tmpdir)
    return config

"""
create a tmp function and return it ( un-invoked ) for later calling
"""
def runGame(emulator):
    """
    create a tmp function and return a pointer
    """
    def tmp():
        try:
            logging.debug("calling process %s" % emulator)
            subprocess.call(emulator + ">/dev/null 2>&1", shell=True)
        except:
            npyscreen.notify_wait("Error launching game, check config")
    return tmp

"""
escape slashes, spaces and whatnot
"""
def sh_escape(s):
   return s.replace("(","\\(").replace(")","\\)").replace(" ","\\ ")


def start(*args, **kwargs):
    #systems = []
    logging.info("Starting")
    # scan for systems
    for dirname, dirnames, filenames in os.walk(romdir):
        print("adding systems in: " + dirname )
        for d in dirnames:
            if getSystemConfig(d).has_section("default"):
                print(d)
                systems.append(d)
        break

    logging.info("Detected Systems: " + str(systems))

    App = RetroBoiApp()
    try:
        App.run()
    except KeyError as e:
        print("unable to instantiate systems, is 'Main' dir present in romdir with default.cfg?")
        print(str(e.message))


def reload(*args, **kwargs):
    npyscreen.notify_wait("Reloading...")
    systems = []
    start()


if __name__ == '__main__':
    start()
