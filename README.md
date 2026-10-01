# FastAPIStarter

A FastAPI template for info2602 students based on the [fullstack fastapi template](https://github.com/fastapi/full-stack-fastapi-template) with a few modifications to make it a layered architecture that combines the best of MVC and service repository pattern. This codebase is structured to reduce the repeatibility of code [(the DRY principle)](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself) as it was demonstrated in class that code is usually repeated when implementing functionality for a CLI app, a headless API, and a fullstack app. When writing software at scale, deduplicating code is important as it makes the codebase easier to maintain, test and scale.

Additionally, this codebase follows an API-first, modern AJAX flow (similar to Lab 8). In essence, this can be summarized as follows. 

1. If we want to have this backend web application render the UI as well, we can implement our **VIEWS** that return our user interface.
2. A small javascript script (`utils.js`) intercepts default form submissions and instead sends an appropriate endpoint to our **api** endpoints

The main advantage of this application structure are plenty:
1. We don't have to implement a jinja based frontend for the application. We can simply implement api endpoints like we did in labs 1-4 
2. We can implement a backend API for a mobile / desktop application (where the view logic resides in java/kotlin/flutter etc)
3. We can implement a backend API that uses a separate frontend like Vue, React, Next, Nuxt etc.
4. We can export the list of endpoints and have other services (like AI agents) consume them 
5. We can implement an app that functions purely from the CLI


## What is the Model View Controller (MVC) pattern?

The MVC pattern is a code pattern that is used to organise the modules of a project and when applied to a project, it usually works as follows:

- **Models** are your SQLModel/SQLAlchemy classes (The classes that become database tables)
- **Controllers** are utility functions used to mutate models and/or perform business logic
- **Views** bind controllers to http routes passing along any user parameters from the request to the controller


## What is the Service repository pattern?

The Service Repository pattern is designed to keep business logic separate from the data access and it aims to separate the codebase into distinct layers.

- **The Repository Layer** acts as a mediator between the application and the data source (the database, files, etc)
- **The Service Layer** sits between the controller and the repository and this is where business logic lives.


The job of the **repository layer** is to handle ***CRUD*** operations on a model. It doesn't care about the rules at the business logic layer, it's only concerned about how to get and manipulate data. 

The job of the **service layer** is to handle the **RULES** of the application. This is where the business logic comes in such as checking to see if a user's authorized to access the data.

## App Structure

This app is structuresd as follows

<pre>
FastAPIStarter
|-- app
|    |- api
|    |- dependencies
|    |- models
|    |- repositories
|    |- schemas
|    |- services
|    |- static
|    |- templates
|    |- utilities
|    |- views
|-- tests/
|-- environment.env
|-- pyptoject.toml
|-- README.md
</pre>

#### App Structure info

##### Main folders
`app` This folder contains all of our application code.

`tests` This contains the tests (unit tests, integration tests, etc) for the application.

##### Folders inside App
`api` This folder contains the endpoints (route fucntions) of our app.

`dependencies` This folder contains the functions that we'd usually use for dependency injection e.g. getting the information of the user who's performing the request, getting a reference to the database, etc

`models` This folder contains the Pydantic / SQLModel / SQLAlchemy models that eventually become database tables. Note that the files in here are strictly those that become database tables. The other models used for request and response validation go in the `schemas` folder

`repositories` files in this folder are used to query the datastore, which depending on the app can be a file, database, another api, etc. Usually though, it's our database.

`services` The business logic of the application lives here.

`schemas` files in this folder specify pydantic / sqlmodel classes that are used for data validation only and *NOT* models that become database tables.

`utilities` This contain generic helper functions

`static` this contains folders that contain css, js, img and other assets we may need when this app is responsible for rendering of the frontend UI>

`templates` this contains our jinja2 templates

`views` this contains the route functions used for when this app is responsible for rendering the frontnend UI

> `environment.env` is included and loaded automatically by `app/config.py`.
> Its contents are unchanged from the original starter configuration.

## Running Tutorial 3

From the project root:

1. `python -m venv venv`
2. `venv\Scripts\activate` on Windows, or `source venv/bin/activate` on Mac/Linux
3. `pip install -e .`
4. `python app/cli.py initialize`

Initialization creates the database tables. Use `python app/cli.py --help`
for the rental commands. See `TUTORIAL_3_README.md` for a complete rental example.


## Using this in production


If you so ever choose to use this template for your own projects, please consider the following:

1. You **WILL** need to modify the default configuration to 
    - Use a database that's more suitable for production. 
    - Change the default secret
    - Change the default environment
2. You may need to tweak additional settings in the `config.py` file for scalability
3. You'd need to look into a database migration / upgrade tool like alembic
4. You may want to dockerize the application for easier deployment
5. You may want to switch from storing cookies in localstorage to only cookies depending on your security needs.