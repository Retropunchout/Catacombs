import random

#room stuff
room_size=[
    "small","large","spacious","cramped"
]
room_mods=[
    "damp","dusty","cold","warm","darkened","brightly lit","musty",
]
room_coverings=[
    "unintelligible scribbling","dark stains","crude paintings","a thick, viscous fluid","complex patterns","peeling paint","crumbling stonework"
]

no_event_text_list=[
    "You enter an empty chamber.",
    "You enter a {size}, {mod} chamber - the walls glisten with moisture.",
    "You enter what looks like a disused alchemy laboratory, littered with broken bottles.",
    "You enter a {size}, {mod} chamber, it looks like you are the first visitor in a long time.",
    "You enter a {size} workshop, it has been picked bare.",
    "You enter a {mod} tunnel, the walls are covered in {covering}",
    "You enter a {size}, but empty room.",
    "You enter what looks like a workshop, broken tools and a few bones are all that's left here.",
    "You enter a {mod} tunnel, burnt out candles line the walls.",
    "You enter a {size} chapel to an unknown god, all signs of who was worshipped here have been scratched away.",
    "You enter a {mod} hall, broken furniture lies on the floor."
    ]

#walking stuff
walking_additions=[
    ". The ground creaks beneath you.",
    ", clawing cobwebs from your face.",
    ". You hear a distant scratching.",
    ". A deathly cold breeze runs past you.",
    ". Distant drums pound in the darkness.",
    ". You hear a strangled cry cut short in the distance.",
    ". You hear a rattling noise somewhere above you.",
    ", a thick mist enveloping your steps.",
    ". A light flickers somewhere in the distance.",
    ". You hear a dull moaning from somewhere below you.",
]


def get_no_event_text():
    text = random.choice(no_event_text_list).format(mod=random.choice(room_mods),size=random.choice(room_size),covering=random.choice(room_coverings))
    return text