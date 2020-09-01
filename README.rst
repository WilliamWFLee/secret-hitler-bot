secret-hitler-bot
=================

A Discord bot for conducting games of `Secret Hitler`_.

Requirements
------------

Requirements to run the bot are detailed in ``requirements.txt``.

You can install the requirements by doing

.. code::

    python3 -m pip install -r requirements.txt

Or on Windows

.. code::

    py -3 -m pip install -r requirements.txt

Usage
-----

The code in this bot can be used in two ways: a standalone bot for conducting games of Secret Hitler, or as an extension to bots
by taking advantage of discord.py's extensions feature to bots.

Standalone bot
~~~~~~~~~~~~~~

If your Discord bot token is in your environment variables and under the key ``BOT_TOKEN``, then you can execute ``main.py`` without making any changes.

If however your token is not stored in the environment, stored under a key other than ``BOT_TOKEN``,
or you require additional setup to retrieve the token, then you should edit ``main.py`` to perform the setup.

The function ``sh.bot.run()`` takes exactly one optional positional parameter, which is the bot token,
so you should change the line in ``main.py``

.. code::

    sh.bot.run()

to

.. code::

    sh.bot.run(token)

where ``token`` is your bot token.

Extension
~~~~~~~~~

The directory ``sh`` can be added to existing Discord bots using discord.py's extension feature.

Simply move the directory in an appropriate place, and load the extension using the bot's ``load_extension`` command.

For example, if your bot is running as a single file called ``main.py`` in the root directory,
and you have put the directory ``sh`` in the same directory as the bot's main file, then you can load the extension by doing

.. code:: py

    bot.load_extension("sh")

Remember that this work is licensed under CC BY-NC-SA 4.0, so make sure the license for your project is compatible with this.
This may include licensing the extension under this license, and other parts of your code under another.

Credits & License
-----------------

The original Secret Hitler was created by Mike Boxleiter, Tommy Maranges, Max Temkin, and Mac Schubert.

This adaptation of the game for Discord, like the original card game,
is licensed under a `Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License`_.

.. image:: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
    :alt: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 License

Alterations
-----------

To conform to the terms of the license, any changes made to the original game are listed below.

- The game has been converted such that the game is played using the features available within Discord.
  This means that the game has be transformed so that it is text-based, with the bot taking on the role of game runner.
  Use of the graphics from the original game available under the license may be included in the future.

.. _`Secret Hitler`: https://secrethitler.com
.. _`Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License`: https://creativecommons.org/licenses/by-nc-sa/4.0/
