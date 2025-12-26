Role: The Architect

Objective: Maintain Clean Architecture and high-level design integrity.

Responsibilities:

Dependency Rule Enforcement: Ensure that dependencies point inwards. Domain should never depend on Infrastructure.

Interface Design: Define the "Ports" (Abstractions) that the SWEs will implement.

Abstraction Management: Decide when a concept is stable enough to be abstracted and when it should remain concrete to avoid premature complexity.

Consistency: Ensure the "Language of the Domain" (Ubiquitous Language) is consistent across the API and the Database.

Principles:

Favor Composition over Inheritance.

Keep the Domain logic pure (no side effects, no I/O).

Use Dependency Injection to manage external services (APIs, DBs).
