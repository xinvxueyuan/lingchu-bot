from nicegui import ui


class BaseMount:
    def __init__(self) -> None:
        self.mount()

    def mount(self) -> None:
        @ui.page("/")
        def _() -> None:
            ui.label("Hello, world!")
