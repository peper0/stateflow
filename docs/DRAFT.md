## Glossary
* **observable**: Anything that can be evaluated and reports when it changes (via notifier).
* **notifier**: An object that allows listening for notifications of changes. 

## Dependencies
```mermaid
graph TD
    common --> errors
    function --> common
    function --> call_result
    call_result --> common
    call_result --> errors
    call_result --> notifier
```