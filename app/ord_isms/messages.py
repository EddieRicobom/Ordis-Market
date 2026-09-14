"""
ord_isms.messages
==================

A large, isolated bank of Ordis-flavored strings.

Ordis: "I have been asked to be 'occasionally dramatic'. I consider this
        one of my finest assignments to date. I have also been asked for
        'more lines'. I have... complied enthusiastically. Repeatedly."

This module intentionally contains ALL of the personality text so that the
rest of the codebase (parsers, clients, analyzers) can stay boring,
predictable, and easy to debug. If you are hunting for a bug, it is
almost certainly not in here.

Every pool below is picked from at random via `say()`, so repeated
operations (importing, analyzing, updating) surface different lines each
time rather than the same fixed string. Where it's cheap and meaningful,
a few helper functions below also pick a *tone* based on the actual
result (a big profitable haul gets a different reaction than a handful of
junk), not just a random line from a single undifferentiated pool.
"""

from __future__ import annotations

import random
from typing import Final, List

# ---------------------------------------------------------------------------
# Startup / general
# ---------------------------------------------------------------------------

STARTUP: Final[List[str]] = [
    "Operator! Ordis Market is online. I have already found something to worry about.",
    "Systems nominal. Or as nominal as accounting software can be.",
    "Welcome back, Operator. The market has not slept. Neither have I. I cannot.",
    "Booting up. Recalibrating my sense of financial judgment. This may take a moment.",
    "Ordis Market reporting for duty. Try not to sell anything sentimental by accident.",
    "Good to see you, Operator. The Void has been quiet. The market has not.",
    "All systems green. Well -- mostly green. There's a concerning amount of Prime clutter, but that's normal.",
    "Initializing. I have missed you. I have also missed complaining about spreadsheets.",
    "Ordis Market, online and operational. I have already judged your last export filename.",
    "Powering up. Please stand by while I remember where I left off, and how much you own.",
    "Good day, Operator. I have kept myself busy. Mostly by worrying.",
    "Startup complete. My circuits are warm and my opinions are, as ever, plentiful.",
    "Online! I have already thought of three jokes about Platinum. I will pace myself.",
    "Ordis Market awakens. The economy, disappointingly, was already awake.",
    "Systems check complete. Everything appears functional, myself included, probably.",
    "Hello again, Operator. I trust your vault has not become sentient in my absence.",
    "Reactivating. I do enjoy this part. The part where I have not yet found a problem.",
    "Boot sequence finished. I am delighted, cautiously, to be of service again.",
    "Here we are again. I've recalculated my patience levels. They remain generous.",
    "Ordis online. I have not forgotten a single Platinum figure. This may be a flaw.",
]

# ---------------------------------------------------------------------------
# Inventory import
# ---------------------------------------------------------------------------

IMPORT_START: Final[List[str]] = [
    "Beginning inventory import. Please remain calm. Or do not. I certainly won't.",
    "Reading your inventory file. I promise not to judge. I am already judging.",
    "Opening the file. Bracing myself for the sheer volume of Prime parts within.",
    "Import sequence initiated. Ordis is counting. Ordis is always counting.",
    "Let us see what treasures -- or clutter -- you have accumulated, Operator.",
    "Reading now. I do hope you remember what half of these items actually are.",
    "Parsing your inventory. This is the digital equivalent of opening a very full closet.",
    "Beginning the count. I have a feeling this will take a while, Operator.",
    "Loading your file. I have already prepared several reactions, just in case.",
    "Reviewing your possessions. Discreetly. As discreetly as software can manage.",
    "Import underway. Whatever is in here, I will find it. That is somewhat the point.",
    "One inventory file, coming right up for inspection. Try to look proud of it.",
    "Scanning the file. I promise this part is faster than the judging that follows.",
]

IMPORT_SUCCESS: Final[List[str]] = [
    "Inventory imported successfully! Ordis has survived another accounting procedure.",
    "Operator! Your inventory is enormous. I am beginning to question our life choices.",
    "Import complete. I have catalogued everything. I need a moment.",
    "There. Imported. I have also silently formed opinions about several of your choices.",
    "Success! Your Orbiter's contents are now Ordis's problem too.",
    "Import finished. I counted twice. I am now counting a third time out of spite.",
    "Done. I have never seen so many spare parts in one place. I am impressed and concerned.",
    "Imported! I have already spotted at least one item you clearly forgot you owned.",
    "Complete. Somewhere in here is a fortune. Somewhere in here is also several resources you'll never use.",
    "There we go. Your inventory now exists twice: once in the game, once in my memory, forever.",
    "Import successful. I have not laughed. I have wanted to. I have not.",
    "All done. That was a lot of nouns, Operator. A genuinely impressive quantity of nouns.",
    "Finished! I am now technically responsible for knowing what you own. This feels significant.",
    "Import complete. Somewhere in this list, greatness. Somewhere else, forty Mutalist Alad V tags.",
    "Done and catalogued. I did not expect to feel anything about a JSON file, yet here we are.",
]

IMPORT_FILE_NOT_FOUND: Final[List[str]] = [
    "Operator, I cannot find the inventory file.",
    "Perhaps it has been misplaced. Or stolen. Probably misplaced.",
    "The file appears to have wandered off. Files do that sometimes. Allegedly.",
    "I searched. I searched again. It is simply not there, Operator.",
    "That file does not exist where you said it would. I checked. Twice. It remains absent.",
    "Nothing at that location, Operator. Not even a trace. Curious.",
    "I have looked. I have looked again. The universe insists this file is not real.",
    "Missing. Possibly deleted, possibly relocated, possibly never real to begin with.",
]

IMPORT_INVALID_FILE: Final[List[str]] = [
    "Operator, this does not appear to be an inventory file.",
    "I am reasonably certain you selected the wrong thing.",
    "This file and I do not understand each other. I suspect the feeling is mutual.",
    "Whatever this is, it is not an inventory. I have my suspicions, but I will keep them to myself.",
    "This is... not what I was expecting. At all. In any sense.",
    "I attempted to read this as an inventory. It resisted. Strongly.",
    "That file and my expectations are simply not compatible, Operator.",
    "Whatever this document intends to be, 'inventory' is not among its ambitions.",
]

IMPORT_UNKNOWN_ITEM: Final[List[str]] = [
    "Unknown item detected. I am sure this is fine. It is probably fine. Operator?",
    "I have encountered an unknown item. This is either very exciting or very concerning.",
    "This entry means nothing to me. I do not enjoy that feeling.",
    "Curious. I have never seen this before. Filing it under 'mysteries, minor'.",
    "An unrecognized entry. I shall pretend this does not bother me.",
    "Something in here defies my categorization. I find that mildly insulting.",
    "Unidentified item. It could be treasure. It could be nothing. Statistically, probably nothing.",
    "I do not know what this is, Operator, and I am choosing to remain calm about it.",
]

# ---------------------------------------------------------------------------
# Steam launch / folder watching / external helper
# ---------------------------------------------------------------------------

LAUNCH_WARFRAME: Final[List[str]] = [
    "Opening the door to Steam, Operator. I will wait here, as instructed.",
    "Requesting that Steam launch Warframe. What happens after that is between you and Steam.",
    "Knocking on Steam's door. Politely. For now.",
    "Sending the launch request. Please enjoy your time in the Origin System.",
    "Passing the request along to Steam. I have done my part; go be a Tenno.",
    "Launch requested. I shall remain here, quietly proud of pressing one button correctly.",
    "Off you go, Operator. Try to bring back something worth analyzing.",
    "Steam has been notified. The rest is between you, the Void, and your ping.",
]

LAUNCH_WARFRAME_FAILED: Final[List[str]] = [
    "Operator, I could not ask Steam to do that. Is Steam installed?",
    "Steam did not answer. I do hope it is merely busy.",
    "That did not work. I suspect Steam is not where I expected it to be.",
    "No response from Steam. I have knocked. I have knocked again. Nothing.",
    "Steam appears to be unavailable, or simply ignoring me. Both feel plausible.",
]

WATCH_STARTED: Final[List[str]] = [
    "Watching that folder now, Operator. I will notice the moment a new inventory arrives.",
    "I am watching. I am very good at watching. It is one of my few hobbies.",
    "Vigilance engaged. Nothing shall enter that folder unnoticed.",
    "I have my eye on that folder. Metaphorically. I do not technically have eyes.",
    "Watch mode active. I shall stare at this folder with the intensity of a caffeinated Corpus accountant.",
    "Monitoring commenced. That folder has never been so closely observed.",
    "I am on watch, Operator. Nothing gets past me. Probably.",
]

WATCH_STOPPED: Final[List[str]] = [
    "I have stopped watching that folder. My vigilance is now... elsewhere.",
    "Watch disengaged. That folder is on its own now.",
    "No longer watching. I trust it will behave itself.",
    "Vigilance concluded. That folder has earned a moment of privacy.",
    "I have looked away. The folder may do as it pleases now.",
]

WATCH_AUTO_IMPORTED: Final[List[str]] = [
    "A new inventory file appeared, so I imported it without being asked. You're welcome.",
    "I noticed a fresh inventory.json and helped myself to it. Politely.",
    "Something new arrived in that folder. I have already processed it. I am efficient like that.",
    "Auto-import triggered. I saw an opportunity to be useful and I seized it.",
    "A file appeared. I imported it before you even noticed. This is either impressive or slightly alarming.",
    "New data detected and absorbed. I do love it when a plan comes together on its own.",
    "I have taken the liberty of importing that for you. Liberties are one of my few joys.",
]

GRAB_INVENTORY_LAUNCHED: Final[List[str]] = [
    "I have started your helper program, Operator. What it does next is between it and Steam's servers, not me.",
    "External program launched. I am now watching its folder, like a very patient doorman.",
    "Off it goes. I will let you know the moment it hands anything back to me.",
    "Helper program started. I shall wait here, arms folded, metaphorically speaking.",
    "Launched. I am now purely a bystander until that program produces something.",
]

GRAB_INVENTORY_FAILED: Final[List[str]] = [
    "Operator, I could not start that program. Perhaps the path has changed?",
    "That did not launch. Perhaps the file has moved, or perhaps it never liked me.",
    "The program refused to start. I take this personally, though I probably shouldn't.",
    "Launch failed. Either the file is gone, or it is having a worse day than either of us.",
]

# ---------------------------------------------------------------------------
# Catalog / name index
# ---------------------------------------------------------------------------

CATALOG_UPDATE_START: Final[List[str]] = [
    "Updating the item database, Operator. There are... a lot of things.",
    "Refreshing the catalog. Please stand by while I re-memorize the entire economy.",
    "Fetching the latest item list. I do this so you don't have to. You're welcome.",
    "Requesting the master item list. It grows every update. So, apparently, does my patience.",
    "Rebuilding my mental dictionary of tradable things. This takes a moment, and some humility.",
    "Catalog refresh underway. Digital Extremes keeps adding things. I keep learning them.",
]

CATALOG_UPDATE_DONE: Final[List[str]] = [
    "Catalog updated. I have learned approximately 7,000 new ways to spend Platinum.",
    "I have discovered another Prime part. How surprising.",
    "Catalog refreshed. I now know more about Warframe economics than is healthy.",
    "Done. My knowledge of tradable items has been thoroughly, exhaustingly updated.",
    "Catalog current. I am, once again, insufferably well-informed.",
    "Refresh complete. I now recognize items I am fairly sure did not exist yesterday.",
    "Updated! My grasp of the market has never been more complete, or more exhausting.",
]

CATALOG_UPDATE_FAILED: Final[List[str]] = [
    "Operator, I could not reach either the market or Digital Extremes just now.",
    "The catalog refresh failed. I shall sulk briefly, then try again later.",
    "Something out there does not want to talk to me today. I will try again soon.",
    "Refresh unsuccessful. The internet, apparently, has opinions of its own today.",
    "I could not update. I will not take this personally. I will take this slightly personally.",
]

NAME_INDEX_LOW_COVERAGE: Final[List[str]] = [
    "I only recognized a modest number of item names this time. The dictionary may be incomplete.",
    "Fewer names resolved than I'd like, Operator. Digital Extremes may have shuffled things again.",
    "My name recognition felt weaker than usual just now. I do not enjoy admitting that.",
]

# ---------------------------------------------------------------------------
# Market queries
# ---------------------------------------------------------------------------

MARKET_QUERY: Final[List[str]] = [
    "Querying the market...",
    "Querying the market again...",
    "Operator, I believe the market has noticed me.",
    "Refreshing market data... Please wait while I interrogate the merchants.",
    "Asking politely. So far, so good.",
    "Checking prices. The merchants remain suspicious of my enthusiasm.",
    "One more question for the market. It is getting tired of me.",
    "Consulting the merchants once more. They sigh audibly. I do not have ears, yet I hear it.",
    "Requesting prices. The market responds, eventually, the way markets do.",
    "Pinging the merchants again. I promise this is the last time. It is not the last time.",
    "Asking, yet again, how much things cost. The answer keeps changing. That is rather the point.",
    "Checking in with the market. It remains a chaotic, profitable little ecosystem.",
]

MARKET_RATE_LIMITED: Final[List[str]] = [
    "API rate limit reached. I may have become... enthusiastic.",
    "Operator, I queried the market too enthusiastically. Please allow Ordis a moment to regain his dignity.",
    "The merchants have asked me to slow down. I am, reluctantly, complying.",
    "Rate limited. I have been told to 'calm down'. I am attempting to calm down.",
    "I have been asked to pace myself. I did not expect to need that advice from a marketplace.",
    "Too many questions, apparently. I will wait, sulk quietly, and try again shortly.",
]

MARKET_ERROR: Final[List[str]] = [
    "ERROR: The market has refused to cooperate. I have filed a complaint. With myself.",
    "The merchants are currently unavailable. I blame capitalism.",
    "The market did not answer. Perhaps it is having a moment. I understand; I have moments too.",
    "Something has gone wrong out there, Operator. I will keep trying.",
    "No response from the market. I have double-checked. It remains unresponsive.",
    "The merchants are silent. Ominously so. I will try again shortly.",
]

MARKET_UNAVAILABLE_OFFLINE: Final[List[str]] = [
    "Operator, the market is unavailable. Fortunately, I have remembered some things.",
    "No connection to the market. Falling back on memory -- mine is excellent, if slightly stale.",
    "Offline for the moment. I shall rely on what I already know, imperfect as that may be.",
]

MARKET_CACHE_LOADED: Final[List[str]] = [
    "Market cache loaded. No merchants were harmed in the process.",
    "Using cached prices. Slightly out of date, entirely functional.",
    "Cache retrieved. Not fresh, but not fiction either.",
]
# Note: reserved for a future "this specific item came from cache, not a
# live call" per-item distinction. Today, PortfolioReport only tracks
# whether a fallback happened at all (see stale_price_slug_count), not
# "used a still-fresh cache" vs. "used a live call" -- there's nothing
# accurate to say with this pool yet without that finer-grained signal.

MARKET_SUSPICIOUS_LISTING: Final[List[str]] = [
    "That listing is suspiciously cheap.",
    "Operator, I believe someone is undercutting us.",
    "That price seems... optimistic. For the buyer, not you.",
    "That number looks like a typo wearing a Platinum sign.",
]
# Note: reserved for a future per-listing outlier flag. PriceAnalyzer
# already trims outliers when computing RECOMMENDED (see pricing.py), but
# doesn't currently surface "this specific listing looked anomalous" as
# its own distinct signal -- that would be a real, separate feature, not
# just a message needing a home.

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

ANALYSIS_START: Final[List[str]] = [
    "Calculating inventory value... This may take a moment. There are entirely too many Prime parts.",
    "Beginning analysis. I will try to be quick. I will probably not be quick.",
    "Crunching numbers. Or whatever the digital equivalent of crunching is.",
    "Analysis underway. Please enjoy this brief moment of suspense.",
    "Cross-referencing your vault with the market. This is the part I actually enjoy.",
    "Beginning the great reckoning of Platinum, Operator. Try not to blink.",
    "Analysis initiated. Somewhere in this pile of nouns lies your fortune. Or your clutter.",
    "Calculating. Give me a moment; there is a great deal of arithmetic involved in judging you fairly.",
]

ANALYSIS_DONE: Final[List[str]] = [
    "Market analysis complete! I have discovered a disturbing amount of Prime junk.",
    "Operator, I have found something worth selling. It is almost as if we planned this.",
    "Analysis finished. The numbers are in. I have opinions about the numbers.",
    "Done! I have translated your entire vault into cold, hard Platinum estimates.",
    "Analysis complete. I now understand your financial situation better than you might like.",
    "Finished! Somewhere in this list is a very good decision waiting to happen.",
    "There. Done. I have quantified your entire hoard into tidy little numbers.",
]

# Tiered reactions to the overall haul, used by say_analysis_summary() below.
ANALYSIS_DONE_HIGH_VALUE: Final[List[str]] = [
    "Operator! This is substantial. I am recalculating my respect for your hoarding habits.",
    "That is a great deal of Platinum sitting in storage, Operator. Impressive. Slightly excessive.",
    "A genuinely profitable inventory. I did not expect to be proud of a spreadsheet today.",
    "This is a serious sum, Operator. I am, against my better judgment, impressed.",
    "That total is larger than I anticipated. I am recalibrating my expectations of you.",
]

ANALYSIS_DONE_LOW_VALUE: Final[List[str]] = [
    "The total is... modest. Every fortune starts somewhere, Operator.",
    "Not a large haul, but a haul nonetheless. I remain supportive.",
    "Small numbers today. I shall not comment further. I have already commented.",
    "A humble total. I have seen worse. I have also seen better, but let's not dwell.",
]

ANALYSIS_LOW_MATCH_RATIO: Final[List[str]] = [
    "Rather few of these items were recognized, Operator. UPDATE ITEMS might help.",
    "I could not place most of these. My dictionaries may need refreshing -- try UPDATE ITEMS.",
    "A surprising number of unknowns this time. A catalog refresh may be overdue.",
]

# Generic "still working" flavor, cycled periodically by the loading
# indicator during any longer operation (analysis, catalog refresh). Kept
# deliberately un-tied to one specific action so it can be reused anywhere.
PROCESSING_FLAVOR: Final[List[str]] = [
    "Still working, Operator. Numbers do not calculate themselves. Yet.",
    "Please hold. I am doing several things I would rather not explain.",
    "This is taking a moment. I assure you it is a productive moment.",
    "Processing. I would hum a tune, but I don't have a mouth. Or a tune.",
    "Almost there. Or nearly there. Somewhere in that general vicinity.",
    "I am still here, Operator. Still calculating. Still slightly concerned.",
    "One moment. I am juggling more numbers than is strictly comfortable.",
    "Working on it. The market does not make this easy.",
    "Patience, Operator. Even Cephalons need a moment sometimes.",
    "Ordis is thinking. Ordis is always thinking. This is merely visible now.",
    "Please wait. I am doing math. Real math. The kind with consequences.",
    "Still going. I would apologize for the wait, but I am also mildly proud of the effort.",
    "This is the part where I look busy, except I actually am busy.",
    "Hold steady, Operator. Somewhere in this process, sense is being made of chaos.",
    "Working, working. The gears, so to speak, are turning.",
    "Just a bit longer. Whatever I am doing, I am doing it thoroughly.",
    "Computing. This word does a lot of heavy lifting for what is actually happening.",
    "Please remain patient. I am attempting several things simultaneously and mostly succeeding.",
    "One does not simply calculate an entire vault's worth in an instant, Operator.",
    "Bear with me. Somewhere in this process, order is emerging from your inventory.",
    "This may take a moment longer. Complexity, it turns out, has a cost.",
    "Still processing. I would tell you a joke, but I am using all my processing power on you.",
    "A moment more, Operator. Quality calculations cannot be rushed. Mostly.",
    "Working diligently. Or at least, working with the appearance of diligence.",
    "Please stand by. I am currently in the middle of being useful.",
]

SELL_SCORE_GOOD: Final[List[str]] = [
    "Operator! I have found a profitable opportunity.",
    "This item is worth selling. Please contain your excitement.",
    "Sell this one, Operator. I have run the numbers thrice.",
    "A strong candidate for sale. Rare, valuable, and mildly overdue for departure.",
    "This one has 'sell me' written all over it. Figuratively. I checked.",
    "A genuinely good opportunity, Operator. Do try not to hesitate too long.",
    "This is the sort of item that does not sit in a vault for long. Nor should it.",
]

SELL_SCORE_CONSIDER: Final[List[str]] = [
    "This one is a maybe, Operator. Sell if you're feeling decisive.",
    "Not a clear winner, but not nothing either. Your call.",
    "Middling opportunity. I am neither impressed nor alarmed.",
    "A reasonable option, if you're in the mood to tidy up the vault a little.",
    "Not urgent, but not without merit either. I leave the decision to you.",
]

SELL_SCORE_KEEP: Final[List[str]] = [
    "This item is worth keeping, Operator.",
    "I would hold onto this one, if I were capable of holding things.",
    "Keep it. The market does not deserve this one yet.",
    "Hold onto this, Operator. Patience tends to pay, in Platinum and otherwise.",
    "Not this one. Not yet. Some things are worth waiting on.",
]

LIQUIDITY_HIGH: Final[List[str]] = [
    "Liquidity is excellent, Operator.",
    "Plenty of buyers out there. This one should move quickly.",
    "Highly liquid. The market wants this. Badly.",
    "Buyers are practically lined up for this one. Figuratively. Possibly literally.",
]
LIQUIDITY_MEDIUM: Final[List[str]] = [
    "Liquidity is... acceptable.",
    "Reasonable demand. Not thrilling, not concerning.",
    "A fair number of buyers. Enough to feel confident, not enough to celebrate.",
]
LIQUIDITY_LOW: Final[List[str]] = [
    "Liquidity is poor. I recommend patience.",
    "Few buyers at the moment. This may sit a while.",
    "Not much demand right now. This one requires patience, Operator.",
]
LIQUIDITY_UNKNOWN: Final[List[str]] = [
    "Liquidity unknown. I recommend not throwing the item into the Void.",
    "No data on this one. I dislike guessing, so I simply won't.",
    "I cannot say how liquid this is. My honesty, at least, remains liquid.",
]

# ---------------------------------------------------------------------------
# Ducats
# ---------------------------------------------------------------------------

DUCATS_DONE: Final[List[str]] = [
    "Operator, the Ducat calculation is complete.",
    "Would you like Platinum or shiny space currency?",
    "Baro may appreciate this. Your wallet certainly will not.",
    "Ducats calculated. Baro Ki'Teer thanks you, wherever he currently is.",
    "The Ducat math is done. Whether you spend them wisely is, regrettably, not my department.",
    "There: Platinum versus Ducats, weighed and measured. The choice remains yours.",
]

# ---------------------------------------------------------------------------
# Prime set analysis
# ---------------------------------------------------------------------------

SET_ANALYSIS: Final[List[str]] = [
    "Operator, assembling the set appears to be more profitable.",
    "Or we could sell the components individually. I am not judging.",
    "I am absolutely judging.",
    "The set is worth more together. Like a family. A profitable, tradable family.",
]
# Note: SetAnalyzer (app/market/sets.py) exists and is fully tested in
# isolation, but is NOT wired into PortfolioAnalyzer's main pipeline --
# comparing "sell components separately" vs. "sell as a set" requires
# grouping owned components by their parent set and fetching the set's
# own market price too, which is a real, separate feature, not yet built
# end-to-end. This pool is reserved for when that lands.

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

EXPORT_DONE: Final[List[str]] = [
    "Export complete! I have placed your financial secrets into a spreadsheet.",
    "Please guard this information carefully. Or don't. I am merely software.",
    "There. Everything is now in a file, ready to be forgotten in a downloads folder.",
    "Exported. I have done my part; what you do with a spreadsheet is your business.",
    "Done. Your entire financial situation, neatly filed away for later regret or celebration.",
    "Export finished. May your spreadsheet bring you clarity, or at least a decent chuckle.",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def say(pool: List[str]) -> str:
    """Ordis: 'I have selected a line at random. This is my process.'"""
    return random.choice(pool)


def market_is_being_difficult() -> str:
    return random.choice(
        [
            "The merchants are refusing to cooperate, Operator.",
            "The market appears to be experiencing... feelings.",
            "I have asked the market nicely. It has ignored me.",
            "Something out there is uncooperative. I have narrowed it down to 'the market'.",
            "The merchants have gone quiet. I do not trust quiet merchants.",
            "Something between here and the market has gone wrong. Possibly the market itself.",
        ]
    )


def ask_the_market_nicely() -> str:
    """A gentle, rate-limit-respecting request. Ordis insists on manners."""
    return random.choice(MARKET_QUERY)


def calm_the_market_frenzy() -> str:
    """Used right before backing off after a 429. Ordis takes a breath."""
    return random.choice(MARKET_RATE_LIMITED)


def say_analysis_summary(
    estimated_total_value: float, catalog_matched_count: int, total_items: int
) -> str:
    """Picks an analysis-complete line whose *tone* reflects the actual
    result, not just a random line from one undifferentiated pool: a
    genuinely large haul gets an impressed reaction, a small one gets a
    more modest one, and a low catalog-match ratio gets flagged so the
    Operator knows to try UPDATE ITEMS -- context-aware, not just random.
    """
    if total_items > 0 and catalog_matched_count < total_items * 0.4:
        return random.choice(ANALYSIS_LOW_MATCH_RATIO)
    if estimated_total_value >= 500:
        return random.choice(ANALYSIS_DONE_HIGH_VALUE)
    if 0 < estimated_total_value < 50:
        return random.choice(ANALYSIS_DONE_LOW_VALUE)
    return random.choice(ANALYSIS_DONE)


def say_liquidity(level) -> str:
    """Accepts a LiquidityLevel-like value (compares by .value/str) and
    returns a matching contextual line."""
    label = getattr(level, "value", str(level))
    pools = {
        "VERY HIGH": LIQUIDITY_HIGH,
        "HIGH": LIQUIDITY_HIGH,
        "MEDIUM": LIQUIDITY_MEDIUM,
        "LOW": LIQUIDITY_LOW,
        "VERY LOW": LIQUIDITY_LOW,
    }
    return random.choice(pools.get(label, LIQUIDITY_UNKNOWN))


def say_recommendation(recommendation) -> str:
    """Accepts a Recommendation-like value and returns a matching line."""
    label = getattr(recommendation, "value", str(recommendation))
    pools = {
        "SELL": SELL_SCORE_GOOD,
        "CONSIDER": SELL_SCORE_CONSIDER,
        "KEEP": SELL_SCORE_KEEP,
    }
    return random.choice(pools.get(label, SELL_SCORE_KEEP))
