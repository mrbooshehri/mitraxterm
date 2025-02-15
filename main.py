from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Tabs, Tree, Button, Input, Select, Label
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen

# Initial tab names
INITIAL_TABS = ["⌂"]  # Only the home tab

# Modal for adding/editing a connection
class ConnectionModal(ModalScreen):
    def __init__(self, connection_data=None):
        super().__init__()
        self.connection_data = connection_data or {}

    def compose(self) -> ComposeResult:
        yield Vertical(
            Input(placeholder="Host", id="host", value=self.connection_data.get("host", "")),
            Input(placeholder="Port", id="port", value=self.connection_data.get("port", "")),
            Input(placeholder="Label", id="label", value=self.connection_data.get("label", "")),
            Input(placeholder="Group", id="group", value=self.connection_data.get("group", "")),
            Input(placeholder="Password", id="password", password=True, value=self.connection_data.get("password", "")),
            Horizontal(
                Button("Save", id="save", variant="success"),
                Button("Cancel", id="cancel", variant="error"),
                id="action_btns",
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            # Gather data from inputs
            host = self.query_one("#host", Input).value
            port = self.query_one("#port", Input).value
            label = self.query_one("#label", Input).value
            group = self.query_one("#group", Input).value
            password = self.query_one("#password", Input).value

            # Return the connection data
            self.dismiss({"host": host, "port": port, "label": label, "group": group, "password": password})
        elif event.button.id == "cancel":
            self.dismiss(None)


# Modal for confirming connection removal
class ConfirmModal(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Are you sure you want to remove this connection?"),
            Horizontal(
                Button("Yes", id="yes", variant="success"),
                Button("No", id="no", variant="error"),
                id="action_btns",
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        elif event.button.id == "no":
            self.dismiss(False)


class Sidebar(Container):
    def compose(self) -> ComposeResult:
        # Create a tree with a root node
        tree = Tree("Connections", id="sidebar-tree")
        tree.root.expand()  # Expand the root node by default
        yield tree

        # Menu button for connection actions
        yield Select(
            options=[
                ("Add Connection", "add"),
                ("Edit Connection", "edit"),
                ("Remove Connection", "remove"),
            ],
            prompt="Connection Menu",
            id="connection-menu",
        )


class PyxTerm(App):

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+s", "toggle_sidebar", "Toggle sidebar"),
        ("ctrl+n", "new_tab", "New tab"),  # Binding for Ctrl+N
        ("ctrl+x", "close_tab", "Close tab"),  # Binding for Ctrl+X
    ]

    CSS = """
        Tabs {
            dock: top;
        }

        Screen {
            layers: sidebar;
        }

        Sidebar {
            width: 30;
            height: 100%;
            dock: left;
            background: brown;
            layer: sidebar;
            transition: offset 0.3s;
        }

        Sidebar.-hidden {
            display: none;
        }

        #sidebar-tree {
            width: 100%;
            height: 80%;
        }

        Select {
            width: 100%;
            margin: 1;
        }

        /* Styling for modals */
        ModalScreen {
            align: center middle;
            width: 50%;
            height: auto;
            background: $surface;
            border: round $primary;
            padding: 1;
        }

        /* Styling for buttons */
        Button.success {
            background: green;
            color: white;
        }

        Button.error {
            background: red;
            color: white;
        }

        Horizontal {
            width: 100%;
            height: auto;
        }

        Vertical {
            width: 100%;
            height: auto;
        }

        #action_btns{
            align: right middle;
            padding: 0 1;
        }
    """

    def __init__(self):
        super().__init__()
        self.tab_counter = len(INITIAL_TABS) + 1  # Start counter after initial tabs
        self.connections = {}  # Store connection data

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield Sidebar(classes="-hidden")
        yield Tabs(*INITIAL_TABS)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_toggle_sidebar(self) -> None:
        """An action to toggle sidebar."""
        sidebar = self.query_one(Sidebar)
        sidebar.toggle_class("-hidden")
        self.notify("Sidebar toggled", timeout=1)

    def action_new_tab(self) -> None:
        """An action to create a new tab."""
        tabs = self.query_one(Tabs)
        new_tab_id = f"tab-{self.tab_counter}"  # Generate a unique tab ID without spaces
        tabs.add_tab(new_tab_id)  # Add the new tab
        tabs.active = new_tab_id  # Focus the new tab
        self.tab_counter += 1  # Increment the counter
        self.notify(f"New tab created: {new_tab_id}", timeout=1)

    def action_close_tab(self) -> None:
        """An action to close the currently focused tab."""
        tabs = self.query_one(Tabs)
        if len(tabs.query("Tab")) > 1:  # Check if there is more than one tab
            active_tab = tabs.active
            tabs.remove_tab(active_tab)  # Remove the active tab
            self.notify(f"Tab closed: {active_tab}", timeout=1)
        else:
            self.notify("Cannot close the last tab", timeout=1)

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle menu selection for connection actions."""
        tree = self.query_one("#sidebar-tree")
        selected_node = tree.cursor_node  # Get the currently selected node

        if event.value == "add":
            # Show the add connection modal
            def handle_add_connection(result):
                if result:
                    # Add the connection to the tree
                    label = result["label"]
                    new_node = tree.root.add(label)
                    new_node.allow_expand = False  # Connections cannot have children
                    self.connections[new_node.id] = result  # Store connection data
                    self.notify(f"Connection added: {label}", timeout=1)

            await self.push_screen(ConnectionModal(), handle_add_connection)

        elif event.value == "edit":
            if selected_node and selected_node != tree.root:
                # Show the edit connection modal with existing data
                connection_data = self.connections.get(selected_node.id, {})

                def handle_edit_connection(result):
                    if result:
                        # Update the connection data and label
                        label = result["label"]
                        selected_node.label = label
                        self.connections[selected_node.id] = result
                        self.notify(f"Connection updated: {label}", timeout=1)

                await self.push_screen(ConnectionModal(connection_data), handle_edit_connection)
            else:
                self.notify("No connection selected", timeout=1)

        elif event.value == "remove":
            if selected_node and selected_node != tree.root:
                # Show the confirmation modal
                def handle_remove_connection(result):
                    if result:
                        # Remove the connection
                        label = selected_node.label
                        selected_node.remove()  # Remove the node from the tree
                        del self.connections[selected_node.id]
                        self.notify(f"Connection removed: {label}", timeout=1)

                await self.push_screen(ConfirmModal(), handle_remove_connection)
            else:
                self.notify("No connection selected", timeout=1)


if __name__ == "__main__":
    app = PyxTerm()
    app.run()
