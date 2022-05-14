# Testing component

Everything is broken here


## Improving

  * Use sqlalchemy transactions

session.begin/flush/rollback

See: https://docs.sqlalchemy.org/en/14/orm/session_transaction.html

  * Test if using update_before_add=False eliminates unknown states

  * Don't override states from database (we can mess statistics)


## Energy panel

Measuares will show… eventually. With or with forcing statistics with `compile_statistics`
