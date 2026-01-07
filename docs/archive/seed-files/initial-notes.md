Notes to self... 

Create a series of prompts to build a stock market emulation web app where users can try out stock strategies without using real money.


The key to the prompts will be to lay a very solid foundation that means agents all align on the work that needs to be done and all work to a high standard.

In fact, the first task should be to create several copilot agents with specific prompts for specific tasks. Planning and architecture, repo maintenance, refactoring, test improvement, cloud infra/deployment pipelines.

Lay out the key technologies that will be used and some of the configuration of those techs. (E.g. python, ruff, pyright, precommit, gha, AWS CDK, taskfile, docker compose, redis, postgres/sqlite), sqlmodel (need to be careful about that one).

Do I want to use reflex? Or just use typescript frontend with python backend? Is the reflex builder good enough? 


What api to use to read stock prices?

What scheduler? APScheduler, event bridge and lambdas, celery, Cron, systemd, etc.?

What way to store data? Influx, postgres, parquet, etc.

Clean architecture.

Test driven design? At least behavior driven tests...


MVP is for user to be able to start an account with $10K, chose to invest in a few different stocks, be able to keep track of the value into as time goes by.


Next is for user to be able to do that from a backdated time and then see how that has performed over time.

Including selling and purchasing more during that time.


Then we will want to start including things like the purchase fees etc. 

Later down the line we want to add ways to automatically apply trading algorithms that activate at various times of the day etc.


The point of the above notes is to be able to keep in mind the direction the code will go as it develops, but we don't need to overly abstract at the beginning.

We will want both live tracking as well as the ability to re-run historical data at the very least.


Can we emphasize behaving like software engineers that follow the philosophies described in the book Modern Software Engineering (does the ai know about this book in it's parametrized data? It would be very helpful if so, but I suspect not... Especially anthropics models).

Really want to highlight the values of meaningful tests that aren't burdensome to write or maintain. Want to emphasize the importance of refactoring often to continually improve the codebase for future development. Not abstracting too early for concepts that aren't definitely needed, but making sure to abstract at a level that makes it easier to be flexible and make changes in the future. Making sure to lean on dependency injection and composition. Keeping classes that store data separate from classes that do things. 



Let's talk about the above plan, start to flesh it out a little, discuss some of the directions and choices, and then we'll start building this project and application after that.
