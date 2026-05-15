from nicegui import ui


async def main() -> None:
    pass


@ui.page(path="/")
async def page() -> None:
    with ui.left_drawer().classes(add="bg-black text-white w-64") as left_drawer:
        ui.label(text="左栏")

    with ui.header(elevated=True).classes(
        add="bg-[#3874c8] text-white flex items-center justify-between h-14 px-4"
    ):
        ui.button(icon="menu", on_click=left_drawer.toggle).props(add="flat dense")
        ui.label(text="头部")

    with ui.row().classes(add="flex-1 bg-[#1274c8] text-white p-4"):
        ui.label(text="右栏")

    with ui.footer(elevated=True).classes(
        add="bg-blue-600 text-white flex items-center justify-center h-12"
    ):
        ui.label(text="底部")


ui.run()
