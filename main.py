import random
import libtcodpy as libtcod
from collections import namedtuple
import copy
import json
from functools import partial

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             OptionProperty, ObjectProperty, StringProperty)
from kivy.lang import Builder
from kivy.animation import Animation

from world_data import get_no_event_text, walking_additions


#% chance
COMBAT_CHANCE = 20
LOOT_CHANCE = 50
NO_EVENT_CHANCE = 20
AREA_LIST = []
ENCOUNTER_LIST = []

class World:
    def __init__(self):
        self.areas = []
        self.characters = []
        self.items = []
        self.deities = []

        self.encounters = {}
        self.monsters = []

        self.current_area = None
        self.current_encounter = None
        self.current_level = 0

        self.good = 0

        #Add modifiers for journey
        self.lucky = False
        self.unlucky = False
        self.violent = False

        def assess_world():
            global LOOT_CHANCE, COMBAT_CHANCE
            if self.lucky:
                LOOT_CHANCE += 10
            if self.unlucky:
                LOOT_CHANCE -= 10
            if self.violent:
                COMBAT_CHANCE += 10



class Deity:
    def __init__(self, name, domain, symbol="none", colour="none"):
        self.name = name
        self.domain = domain
        self.symbol = symbol
        self.colour = colour

        self.history = ""

class Character:
    def __init__(self, name, hp, strength, dexterity, intelligence, charisma, tags, armour=0, damage=0, crit_chance=1, level=0):
        self.name = name
        self.hp = hp
        self.base_strength = strength
        self.base_dexterity = dexterity
        self.base_intelligence = intelligence
        self.base_charisma = charisma
        self.tags = tags

        self.base_armour = armour
        self.base_damage = damage
        self.base_crit_chance = crit_chance

        self.level = level

        self.inventory = []

        self.poison_counter = 0
        self.bleed_counter = 0

    @property
    def strength(self):
        bonus = sum(equipment.str_mod for equipment in get_all_equipped(Player))
        return self.base_strength + bonus

    @property
    def dexterity(self):
        bonus = sum(equipment.dex_mod for equipment in get_all_equipped(Player))
        return self.base_dexterity + bonus

    @property
    def intelligence(self):
        bonus = sum(equipment.int_mod for equipment in get_all_equipped(Player))
        return self.base_intelligence + bonus
    @property
    def charisma(self):
        bonus = sum(equipment.chr_mod for equipment in get_all_equipped(Player))
        return self.base_charisma + bonus

    @property
    def armour(self):
        bonus = sum(equipment.armour for equipment in get_all_equipped(Player))
        return self.base_armour + bonus

    @property
    def damage(self):
        bonus = sum(equipment.damage for equipment in get_all_equipped(Player))
        return self.base_damage + bonus

    @property
    def crit_chance(self):
        bonus = sum(equipment.crit_chance for equipment in get_all_equipped(Player))
        return self.base_crit_chance + bonus

class Area:
    def __init__(self, name, area_type, description, levels, tags, depth=0):
        self.name = name
        self.area_type = area_type
        self.description = description
        self.levels = levels
        self.tags = tags
        self.depth = depth

        self.encounter_list = []

    def fill_encounter_list(self):

        for x in xrange(self.levels):
                # create combat
            if random.randint(0, 100) < COMBAT_CHANCE:
                self.encounter_list.append(Encounter(name="combat", description="", tags=[], item_tags=[], options=[]))

                # or encounter
            else:
                if random.randint(0, 100) < NO_EVENT_CHANCE:
                    move_opt = Option(description="Move Onwards", tags=[], check="", check_num=0, reward={"onward": ""}, failure={"onward": ""})
                    self.encounter_list.append(Encounter(name="empty_area", description=get_no_event_text(), tags=[], item_tags=[], options=[move_opt]))
                else:
                    for enc in randomly(session_world.encounters.values()):
                        if session_world.current_area.area_type in enc.tags or "neutral" in enc.tags:
                            session_world.current_encounter = enc


class Item:
    def __init__(self, name, item_type, tags, damage, armour, equipment=False, hp_mod=0, str_mod=0, dex_mod=0, int_mod=0, chr_mod=0, crit_chance=0, depth=0):
        self.name = name
        self.item_type = item_type
        self.tags = tags

        self.damage = damage
        self.armour = armour

        self.hp_mod = hp_mod
        self.str_mod = str_mod
        self.dex_mod = dex_mod
        self.int_mod = int_mod
        self.chr_mod = chr_mod
        self.crit_chance = crit_chance

        self.equipment = equipment
        self.is_equipped = False

        self.depth = depth

    def __repr__(self):
        if self.item_type == "weapon":
            ret_string = "{}({}-dexmod{})".format(self.name, str(self.damage), str(self.dex_mod))
        elif self.item_type == "armour":
            ret_string = "{}({})".format(self.name, str(self.armour))
        else:
            ret_string = "{}".format(self.name)

        return ret_string

    def toggle_equip(self):  #toggle equip/dequip status
        if self.item_type in ["weapon","armour"]:
            if self.is_equipped:
                self.dequip()
            else:
                self.equip()

    def equip(self):
        #if the slot is already being used, dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.item_type)
        if old_equipment is not None:
            old_equipment.dequip()

        #equip object and show a message about it
        self.is_equipped = True
        print 'equipped' + self.name

    def dequip(self):
        #dequip object and show a message about it
        if not self.is_equipped: return
        self.is_equipped = False
        print 'deequipped' + self.name

class Encounter:
    def __init__(self,name, description, tags, item_tags, options):
        self.name = name
        self.description = description

        self.tags = tags
        self.item_tags = item_tags

        self.options = options



    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        json_dict = json.load(json_str)
        return cls(**json_dict)

class Option:
    def __init__(self, description, tags, check, check_num, reward, failure):
        self.description = description
        self.tags = tags

        self.check = check
        self.check_num = check_num

        self.reward= reward
        self.failure = failure


        #modifiers

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        json_dict = json.load(json_str)
        return cls(**json_dict)

    def roll(self):
        roll = random.randint(0, 10)

        #check if player stats beat check
        if self.check == "strength":
            if Player.strength > self.check_num:
                roll += 1
        if self.check == "dexterity":
            if Player.dexterity > self.check_num:
                roll += 1
        if self.check == "intelligence":
            if Player.intelligence > self.check_num:
                roll += 1
        if self.check == "charisma":
            if Player.charisma > self.check_num:
                roll += 1

        #tag modifiers
        if "luck" in Player.tags:
            roll += random.randint(1,2)

        if "hard" in self.tags:
            roll -= 1

        if "very hard" in self.tags:
            roll -= 2

        if roll > 8:
            return True
        else:
            return False

class Combat:

    def light_attack(self, attacker, victim):
                crit_string = ''
                # roll to hit
                hit_roll = random.randint(1, 6)
                if attacker.dexterity > victim.dexterity:
                    hit_roll += 1

                # attack hits
                if hit_roll > 2:
                    # add random damage
                    damage = max(0, attacker.damage + random.randint(0, 5))
                    #get crit
                    if self.check_critical(attacker):
                        damage = damage*1.5
                        crit_string = " It is a critical hit!"
                        if "poison" in attacker.tags and random.randint(0, 100) > 50:
                            victim.tags.append("poisoned")
                            victim.poison_counter = random.randint(3, 6)
                            crit_string += " The {} is poisoned.".format(victim.name)
                        if "bleed" in attacker.tags and random.randint(0, 100) > 50:
                            victim.tags.append("bleeding")
                            victim.bleed_counter = 5
                            crit_string += " The {} is bleeding.".format(victim.name)
                    # remove armour negation
                    damage -= victim.armour
                    damage = round(max(1, damage), 0)
                    # deal damage
                    victim.hp -= damage

                    result_string = "{} hits {} for {}.".format(attacker.name, victim.name, str(damage))
                    if crit_string != '':
                        result_string += crit_string
                else:
                    result_string = "{} misses the {}.".format(attacker.name, victim.name)

                return result_string

    def heavy_attack(self, attacker, victim):
                crit_string = ''
                # roll to hit
                hit_roll = random.randint(1, 6)
                if attacker.dexterity > victim.dexterity:
                    hit_roll += 1

                # attack hits
                if hit_roll > 5:
                    # add random damage
                    damage = max(0, attacker.damage + random.randint(-3, 6))
                    #get crit
                    if self.check_critical(attacker):
                        damage = damage*1.8
                        crit_string = " It is a critical hit!"
                        if "poison" in attacker.tags and random.randint(0,100) > 50:
                            victim.tags.append("poisoned")
                            victim.poison_counter = random.randint(3,6)
                            crit_string += " The {} is poisoned.".format(victim.name)
                        if "bleed" in attacker.tags and random.randint(0,100) > 50:
                            victim.tags.append("bleeding")
                            victim.bleed_counter = 5
                            crit_string += " The {} is bleeding.".format(victim.name)
                    # remove armour negation, with slightly less due to heavy
                    damage -= round(victim.armour / 1.5, 0)
                    damage = (max(0, damage))
                    # deal damage
                    victim.hp -= damage

                    result_string = "{} hits {} for {}.".format(attacker.name, victim.name, str(damage))
                    if crit_string != '':
                        result_string += crit_string
                else:
                    result_string = "{} misses the {}.".format(attacker.name, victim.name)

                return result_string

    def heal(self, target):
        heal = random.randint(5,10)
        heal += target.charisma
        target.hp += random.randint(10, 20)

    def cast_spell(self, attacker, victim):
        spell_name_list = ["Darkness seethes from the {} towards the {}, causing {} damage.", "Tendrils rip forth from {} to the {}, causing {} damage."]
        crit_string = ''
        # roll to hit
        hit_roll = random.randint(1, 6)
        if attacker.intelligence > victim.intelligence:
            hit_roll += 1

        # attack hits
        if hit_roll > 5:
            # add random damage
            damage = max(0, attacker.intelligence + random.randint(-3, 6))
            # get crit
            if self.check_critical(attacker):
                damage = damage * 1.8
                crit_string = " It is a critical hit!"
            # remove intelligence negation, with slightly less due to heavy
            damage -= round(victim.intelligence / 1.3, 0)
            damage = (max(0, damage))
            # deal damage
            victim.hp -= damage

            result_string = random.choice(spell_name_list).format(attacker.name, victim.name, str(damage))
            if crit_string != '':
                result_string += crit_string
        else:
            result_string = "{} misses the {}.".format(attacker.name, victim.name)

        return result_string

    def retreat(self, attacker, victim):
            roll_to_retreat = random.randint(1,10)
            roll_to_retreat += victim.dexterity
            roll_to_retreat -= attacker.dexterity

            if roll_to_retreat > 5:
                return True
            else:
                return False

    def status_check(self, player, monster):

        #bleeding is random damage, poison is random length

        if "poisoned" in player.tags:
            player.hp -= 1
            player.poison_counter -= 1
            if player.poison_counter == 0:
                player.tags.remove('poisoned')

        if "bleeding" in player.tags:
            player.hp -= random.randint(1,3)
            player.bleed_counter -= 1
            if player.bleed_counter == 0:
                player.tags.remove('bleeding')

        if "poisoned" in monster.tags:
            monster.hp -= 1
            monster.poison_counter -= 1
            if player.poison_counter == 0:
                player.tags.remove('poisoned')

        if "bleeding" in monster.tags:
            monster.hp -= random.randint(1,3)
            monster.bleed_counter -= 1
            if player.bleed_counter == 0:
                player.tags.remove('bleeding')

        if monster.hp <= 0:
            return "monster_dead"

    def check_critical(self, attacker):
        crit_chance = 10
        crit_chance += attacker.crit_chance
        if random.randint(0,100) < crit_chance:
            return True
        else:
            return False

    def check_spell_critical(self, attacker, victim):
        crit_chance = 10
        crit_chance += attacker.crit_chance
        if attacker.intelligence * 1.5 > victim.intelligence:
            crit_chance += 5
        if random.randint(0,100) < crit_chance:
            return True
        else:
            return False


#system stuff
class LongpressButton(Factory.Button):
    __events__ = ('on_long_press',)

    long_press_time = Factory.NumericProperty(1)

    def on_state(self, instance, value):
        if value == 'down':
            lpt = self.long_press_time
            self._clockev = Clock.schedule_once(self._do_long_press, lpt)
        else:
            self._clockev.cancel()

    def _do_long_press(self, dt):
        self.dispatch('on_long_press')

    def on_long_press(self, *largs):
        pass



Builder.load_string("""
<AutoScrollableVLabel>:
    label: __label
    Label:
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
        id: __label
        text: root.text
        font_name: root.font_name
        font_size: root.font_size
        line_height: root.line_height
        bold: root.bold
        italic: root.italic
        halign: root.halign
        valign: root.valign
        color: root.color
        max_lines: root.max_lines
        
<AutoScrollableHLabel>:
    label: __label
    Label:
        size_hint_x: None
        height: root.height
        width: self.texture_size[0]
        id: __label
        text: root.text
        font_name: root.font_name
        font_size: root.font_size
        line_height: root.line_height
        bold: root.bold
        italic: root.italic
        halign: root.halign
        valign: root.valign
        color: root.color
        max_lines: root.max_lines
""")


class AutoScrollableLabel(object):
    label = ObjectProperty(None)
    autoscroll = BooleanProperty(True)
    duration = NumericProperty(10)
    duration = BooleanProperty(False)
    delay = NumericProperty(1)
    text = StringProperty('')
    font_name = StringProperty('Roboto')
    font_size = NumericProperty('15sp')
    line_height = NumericProperty(1.0)
    bold = BooleanProperty(False)
    italic = BooleanProperty(False)
    color = ListProperty([1, 1, 1, 1])
    max_lines = NumericProperty(0)
    orientation = OptionProperty('vertical', options=['horizontal', 'vertical', 'oneline'])
    valign = OptionProperty('bottom', options=['bottom', 'middle', 'top'])
    halign = OptionProperty('left', options=['left', 'center',
                                             'right', 'justify'])

    l_size_hint_x = NumericProperty(1, allownone=True)
    l_size_hint_y = NumericProperty(1, allownone=True)

    def on_autoscroll(self, instance, scroll):
        if scroll:
            Clock.schedule_once(self.do_scroll, self.delay)

    def do_scroll(self, *args):
        if self.orientation == 'vertical':
            anim = Animation(scroll_y=0, duration=self.duration)
        else:
            anim = Animation(scroll_x=1, duration=self.duration)
        anim.start(self)

    def on_text(self, instance, text):
        if self.autoscroll:
            Clock.schedule_once(self.do_scroll, self.delay)


class AutoScrollableVLabel(AutoScrollableLabel, ScrollView):

    def __init__(self, **kwargs):
        super(AutoScrollableVLabel, self).__init__(**kwargs)
        self.orientation = 'vertical'


class AutoScrollableHLabel(AutoScrollableLabel, ScrollView):

    def __init__(self, **kwargs):
        self.orientation = 'horizontal'
        super(AutoScrollableHLabel, self).__init__(**kwargs)

def none_to_empty(s):
    return "" if s is None else s

def format_without_nones(format_string, *args):
    return format_string.format(*map(none_to_empty, args))

def get_equipped_in_slot(slot):  #returns the equipment in a slot, or None if it's empty
    for obj in Player.inventory:
        if obj.item_type == slot and obj.is_equipped:
            return obj
    return None

def get_all_equipped(obj):  #returns a list of equipped items
    if obj == Player:
        equipped_list = []
        for item in Player.inventory:
            if item.is_equipped:
                equipped_list.append(item)
        return equipped_list
    else:
        return []  #other objects have no equipment

def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())

def json2obj(data): return json.load(data, object_hook=_json_object_hook)

def combine_funcs(*funcs):
    def combined_func(*args, **kwargs):
        for f in funcs:
            f(*args, **kwargs)

    return combined_func

def randomly(seq):
    shuffled = list(seq)
    random.shuffle(shuffled)
    return shuffled

def create_area():
        libtcod.namegen_parse('language_data.txt')

        area_type = random.choice(["crypt", "castle"])

        #make sure name isn't the same as it's confusing
        area_name_correct = False
        name_list = []
        for area in AREA_LIST:
            name_list.append(area.name)

        while area_name_correct == False:

            area_name = libtcod.namegen_generate(area_type)
            if area_name not in name_list:
                area_name_correct = True

        area = Area(name=area_name, area_type=area_type, description="", levels=random.randint(5, 10), tags=[])
        area_tags = []

        if area_type == "crypt":
            area_tags = random.choice(["dark", "cursed"])
        elif area_type == "castle":
            area_tags = random.choice(["dark", "cursed"])


        area.tags = area_tags

        area.fill_encounter_list()

        return area



def init():
    global Player, session_world
    session_world = World()
    libtcod.namegen_parse('language_data.txt')
    #create world
    for x in xrange(random.randint(10,20)):
        area = create_area()
        session_world.areas.append(area)



    #create deities
    for i in range(5):
        domains = ["light","dark","fire","ice","earth","air","war","peace"]
        deity_name = libtcod.namegen_generate("deity_names")
        symbols = libtcod.namegen_generate("symbols")
        colours = libtcod.namegen_generate("colours")
        deity = Deity(name=deity_name,domain=random.choice(domains),symbol=symbols, colour= colours)
        session_world.deities.append(deity)
        print deity.name

    #init player
    Player = Character(name="Player", hp=10,strength=5, dexterity=5,intelligence=5,charisma=5,tags=[])
    dagger = Item(name='Dagger', item_type="weapon", tags=[], damage=1, armour=0)
    axe = Item(name='Axe', item_type="weapon", tags=[], damage=12, armour=0, dex_mod=-2)
    torch = Item(name='Torch', item_type="utility", tags=["light"], damage=0, armour=0)
    clothes = Item(name='Clothing', item_type="armour", tags=["light"], damage=0, armour=1)
    Player.inventory.append(dagger)
    Player.inventory.append(axe)
    Player.inventory.append(torch)
    Player.inventory.append(clothes)

    #read general encounters
    with open('encounters.json') as enc_json:
        encs = json.load(enc_json)
        for enc in encs["encounters"]:
            encounter = Encounter(name=enc["name"],description=enc["description"],tags=enc["tags"],item_tags=enc["item_tags"],options=enc["options"])
            options = encounter.options
            encounter.options = []
            for opt in options:
                option = Option(description=opt["description"],tags=opt["tags"],check=opt["check"],check_num=opt["check_num"], reward=opt["reward"], failure=opt["failure"])
                encounter.options.append(option)

            session_world.encounters[encounter.name] = encounter

    #deitys
    for deity in session_world.deities:
        pray_option=Option("Pray to {}".format(deity.name),tags=[],check="intelligence",check_num=1,reward={"blessing":"You receive a blessing from {}".format(deity.name)},failure={"curse":"{} curses you!".format(deity.name)})
        leave_option = Option("Leave", tags=[], check="none", check_num=1,
                             reward={"nothing": "You continue onwards."}, failure={"nothing": "You continue onwards."})

        shrine_modifier = libtcod.namegen_generate("general_modifiers")
        shr_start = ["You come across a {} shrine to {}, ", "Ahead you see a {} shrine dedicated to {}, "]
        shr_end = ["it is covered with {} {}s", "it is adorned with a {} {}", "littered with icons of {} {}s", "in the center is a statue of a {} {}"]
        shrine_phrase = random.choice(shr_start)+random.choice(shr_end)

        encounter = Encounter(name="shrine of {}".format(deity.name),description=shrine_phrase.format(shrine_modifier,deity.name,deity.colour,deity.symbol),tags=[deity.domain],item_tags={"item":"none","desc":"","reward":"nothing"},options=[pray_option, leave_option])

        session_world.encounters[encounter.name] = encounter

    #monsters
    with open('monsters.json') as enc_json:
        mons = json.load(enc_json)
        for mon in mons:
            monster = Character(name=mon["name"], hp=mon["hp"], strength=mon["strength"], dexterity=mon["dexterity"], intelligence=mon["intelligence"], charisma=mon["charisma"], armour=mon["armour"], damage=mon["damage"], tags=mon["tags"], level=mon["level"])
            session_world.monsters.append(monster)

    #add items
    with open('items.json') as enc_json:
        items = json.load(enc_json)
        for ite in items["items"]:
            item = Item(name=ite["name"], item_type=ite["item_type"], tags=ite["tags"], damage=ite["dmg"], armour=ite["armour"], depth=ite["depth"])

            #add modifier search so JSON isn't so redic
            if "crit_chance" in ite:
                item.crit_chance = ite["crit_chance"]
            if "dex_mod" in ite:
                item.dex_mod = ite["dex_mod"]
            if "int_mod" in ite:
                item.int_mod = ite["int_mod"]
            if "str_mod" in ite:
                item.str_mod = ite["str_mod"]
            session_world.items.append(item)

    #start first area
    session_world.current_area = Area(name="Crumbling Ruins",area_type="cave", description="A cave network filled with crumbling ruins",levels=5,tags=[],depth=1)
    session_world.current_area.fill_encounter_list()

    total_levels = 0
    #create world and populate
    for x in xrange(random.randint(7,10)):
        area = create_area()
        AREA_LIST.append(area)

    num_of_areas = len(AREA_LIST)

    depth_num =2
    for area in AREA_LIST:
        area.depth = depth_num
        depth_num +=1
        print area.name + str(area.depth)


    for area in AREA_LIST:
        total_levels += area.levels


    #search list for reasonable start:
    for enc in session_world.current_area.encounter_list:
        if enc.name != 'combat':
            session_world.current_encounter = enc




class Game(BoxLayout):

    def __init__(self, **kwargs):
        super(Game, self).__init__(**kwargs)
        self.orientation='vertical'

        #top level
        self.top_level = GridLayout()
        self.top_level.cols = 2
        self.header_label = Label(text='The Catacombs',size_hint_y=None, height=50)
        self.top_level.add_widget(self.header_label)

        self.exit_button = Button(text='exit', size_hint_x=None,size_hint_y=None, width=50, height=50)
        #self.exit_button.bind()
        self.top_level.add_widget(self.exit_button)
        self.add_widget(self.top_level)

        #encounter/text window
        self.encounter_container = ScrollView(size=(200,100), valign= 'top')
        self.encounter_text = Label(text=session_world.current_encounter.description,strip=True, text_size=(200,None),halign= 'left',valign= 'top' )
        self.encounter_container.add_widget(self.encounter_text)
        self.add_widget(self.encounter_container)

        self.player_text = Label(text=Player.name, strip=True)
        self.add_widget(self.player_text)

        self.option_layout = BoxLayout(orientation='vertical')

        self.add_widget(self.option_layout)

        self.update_all(emitter='efa')



    def fill_options(self):
        self.option_layout.clear_widgets()
        for option in session_world.current_encounter.options:
            self.opt = Button(text=option.description)
            self.opt.bind(on_press=partial(self.use_option,opt_pick=option))
            self.option_layout.add_widget(self.opt)
        #add inventory button
        self.inventory_button = Button(text='Inventory')
        self.inventory_button.bind(on_press=self.show_inventory)
        self.option_layout.add_widget(self.inventory_button)


    def use_option(self, emitter, opt_pick):
        #use item, equip item or use the option
        #worked var needed for some reason...
        worked_var = False
        if isinstance(opt_pick, Item):
            if opt_pick.item_type == "weapon" or "armour":
                opt_pick.toggle_equip()
            # if opt_pick.item_type not in ["weapon", "armour"]:
            #     if session_world.current_encounter.item_tags["item"] in opt_pick.tags:
            #         worked_var = True
            # else:
            #     if opt_pick.item_type == "weapon" or "armour":
            #         opt_pick.toggle_equip()
            self.inv_view.dismiss()
            self.update_all('emitter')


            if worked_var == True:
                self.encounter_text.text = session_world.current_encounter.item_tags["desc"]
                self.opt_result(opt_pick=opt_pick)
                self.move_option()

        #use options
        else:
            roll_result = opt_pick.roll()
            if roll_result == True:
                self.encounter_text.text = opt_pick.reward.values()[0]
                self.opt_result(opt_pick=opt_pick)
                self.move_option()
            else:
                self.encounter_text.text = opt_pick.failure.values()[0]
                self.opt_result(opt_pick=opt_pick)
                self.move_option()


    def opt_result(self, opt_pick):
        if isinstance(opt_pick, Item):
            key = session_world.current_encounter.item_tags["reward"]
        else:
            key = opt_pick.reward.keys()[0]

        if key == "nothing":
            print "nothing"
        elif key == "charisma":
            Player.charisma += 1
        elif key == "strength":
            Player.strength += 1
        elif key == "dexterity":
            Player.dexterity += 1
        elif key == "intelligence":
            Player.intelligence += 1
        elif key == "damage":
            Player.hp -= random.randint(5, 10)
        elif key == "onwards":
             self.next_level("")
        else:
            pass
            #item = session_world.items[opt_pick.reward.keys()[0]]
            #Player.inventory[item.name] = item


    def move_option(self):
        self.option_layout.clear_widgets()
        self.opt = Button(text="Go onwards.")
        self.opt.bind(on_press=combine_funcs(self.next_level,self.update_all))
        self.option_layout.add_widget(self.opt)




    def next_area(self):
        # check for next highest level.
        next_int = session_world.current_area.depth + 1
        for area in AREA_LIST:
            if area.depth == next_int:
                session_world.current_area = area
                break
        else:
            #end the game
            end_text = "You step into a pitch black room, you feel hands grabbing at you, dragging you down. You know this isn't the end."
            session_world.current_encounter = Encounter(name="", description=end_text, tags=[], item_tags=[], options=[])

        #sort out new area
        session_world.current_level = 1
        session_world.current_area.fill_encounter_list()

        new_area_text = "Ahead, you see the entrance to the {}".format(session_world.current_area.name)

        move_opt = Option("Go onwards",tags=[],check="",check_num=1,reward={"onwards":"You enter the {}.".format(session_world.current_area.name)},failure={"onwards":"You enter the {}".format(session_world.current_area.name)})
        session_world.current_encounter = Encounter(name="new_area", description=new_area_text, tags=[], item_tags=[], options=[move_opt])


        self.header_label.text = "{} - {}".format(session_world.current_area.name,session_world.current_area.depth)
        self.update_all("")


    def next_level(self, emitter):
        enc_list = session_world.current_area.encounter_list

        session_world.current_level += 1
        if len(enc_list) == 1:
            self.next_area()
        else:
            print "---"+session_world.current_area.name
            for enc in enc_list:
                print enc.name
            #remove current encounter
            if session_world.current_encounter in enc_list:
                enc_list.remove(session_world.current_encounter)

            session_world.current_encounter = random.choice(enc_list)

            #if combat enc, run combat
            if session_world.current_encounter.name == "combat":
                self.create_combat()



    def end_combat(self, monster):
        loot = self.loot(monster)
        end_text = "You have killed the {}. ".format(monster.name)
        if loot != "" and loot is not None:
            end_text += "You loot the body, finding a "+ loot.name
        session_world.current_encounter.description = end_text

        self.update_all('')
        self.move_option()

    def loot(self, monster):
        if "creature" not in monster.tags and random.randint(0,100) < LOOT_CHANCE:
                for item in randomly(session_world.items):
                    if item.depth <= session_world.current_area.depth:
                        Player.inventory.append(item)
                        return item
        else:
            return ""


    def create_combat(self):
        combat = Combat()

        #create monster
        for monster in randomly(session_world.monsters):
            if monster.level == session_world.current_area.depth:
                selected_monster = copy.copy(monster)
                break

        def light_attack(emitter):
            msg_return = combat.light_attack(victim=selected_monster, attacker=Player)
            self.msgs += "\n" + msg_return
            if combat.status_check(player=Player, monster=selected_monster) == "monster_dead":
                self.view.dismiss()
                self.end_combat(monster=selected_monster)
            else:
                update_text()
                enemy_turn('')

        def heavy_attack(emitter):
            msg_return = combat.light_attack(victim=selected_monster, attacker=Player)
            self.msgs += "\n" + msg_return
            if combat.status_check(player=Player, monster=selected_monster) == "monster_dead":
                self.view.dismiss()
                self.end_combat(monster=selected_monster)
            else:
                update_text()
                enemy_turn('')


        def retreat(emitter):
            retreat_success = combat.retreat(attacker=selected_monster, victim=Player)
            if retreat_success:
                self.view.dismiss()
                self.move_option()
            else:
                self.msgs += "You cannot escape!"
                update_text()
                enemy_turn('')

        #enemy AI
        def enemy_turn(emitter):
            #choose attack type
            if "healer" in selected_monster.tags and selected_monster.hp > 20 and random.randint(0, 100) < 40:
                msg_return = combat.heal(target=selected_monster)

            elif "caster" in selected_monster.tags:
                msg_return = combat.cast_spell(victim=Player, attacker=selected_monster)

            elif selected_monster.dexterity > selected_monster.strength:
                msg_return = combat.light_attack(victim=Player, attacker=selected_monster)
            else:
                msg_return = combat.heavy_attack(victim=Player, attacker=selected_monster)

            self.msgs += "\n" + msg_return
            update_text()

            return msg_return

        def update_text():
            self.log.text = self.msgs
            player_stats = self.get_char_string(char=Player)
            monster_stats = self.get_char_string(char=selected_monster)

            self.player_stats.text=player_stats
            self.monster_stats.text=monster_stats



        self.msgs = ""


        self.view = ModalView(auto_dismiss=False, size_hint=(.8, .8))
        self.combat_ui = BoxLayout(orientation='vertical')

        player_stats = self.get_char_string(char=Player)
        monster_stats = self.get_char_string(char=selected_monster)
        self.monster_stats = Label(text=monster_stats)

        self.log = AutoScrollableVLabel(text=self.msgs, pos_hint={"right":1.2}, size_hint=(1.1,1.3))

        self.light_attack = Button(text="light attack", on_press = light_attack)
        self.heavy_attack = Button(text="heavy attack", on_press = heavy_attack)
        self.inventory = Button(text="inventory")
        self.retreat = Button(text="retreat", on_press = retreat)
        self.inventory.bind(on_press=combine_funcs(self.show_inventory,enemy_turn))

        self.player_stats = Label(text=player_stats)

        self.combat_ui.add_widget(self.player_stats)

        self.combat_ui.add_widget(self.log)

        self.button_box = BoxLayout()
        self.button_box.add_widget(self.light_attack)
        self.button_box.add_widget(self.heavy_attack)
        self.button_box.add_widget(self.inventory)
        self.button_box.add_widget(self.retreat)
        self.combat_ui.add_widget(self.button_box)

        self.combat_ui.add_widget(self.monster_stats)


        self.view.add_widget(self.combat_ui)

        self.view.open()


    #inventory
    def show_inventory(self, emitter):
        # create content and add it to the view

        self.inv_view = ModalView(auto_dismiss=True, size_hint=(.8, .8))
        self.inventory_grid = GridLayout(row_force_default=True, row_default_height=100, row_default_width=100)
        self.inventory_grid.cols = 4
        self.inv_view.add_widget(self.inventory_grid)
        self.fill_inventory()
        content = Button(text='Close')

        self.inventory_grid.add_widget(content)

        # bind the on_press event of the button to the dismiss function
        content.bind(on_press=self.inv_view.dismiss)

        # open the view
        self.inv_view.open()

    def drop_item(self,emitter,item):
        if item.item_type in ["weapon","armour"]:
            item.toggle_equip()
            Player.inventory.remove(item)

        self.fill_inventory()
        self.update_all('')


    def fill_inventory(self):
        self.inventory_grid.clear_widgets()
        for item in Player.inventory:
            item_but = LongpressButton(text=item.name)
            item_but.bind(on_release=partial(self.use_option,opt_pick=item),on_long_press=partial(self.drop_item, item=item))
            self.inventory_grid.add_widget(item_but)


    def get_char_string(self, char):
        string = format_without_nones("{} | HP:{} | STR:{} | DEX:{} | INT:{} | CHR:{}", char.name, char.hp, char.strength, char.dexterity,
                                      char.intelligence, char.charisma)
        if char == Player:
            weapon_equipped = get_equipped_in_slot("weapon")
            off_hand_equipped = get_equipped_in_slot("off_hand")
            armour_equpped = get_equipped_in_slot("armour")
            player_string = format_without_nones("\n MH:{} | OH:{} | ARM: {}", weapon_equipped, off_hand_equipped, armour_equpped)

            return string + player_string

        else:

            return string

    def update_all(self, emitter):
        self.player_text.text = self.get_char_string(char=Player)

        self.encounter_text.text = session_world.current_encounter.description
        self.fill_options()


class MyApp(App):

    def build(self):
        init()
        return Game()


if __name__ == '__main__':
    MyApp().run()
