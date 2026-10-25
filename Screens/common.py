"""Gemeinsame Bausteine für Screens und Listen."""

import flet as ft


def page_heading(title: str, subtitle: str, action=None):
    title_block = ft.Column(
        [
            ft.Text(title, size=28, weight=ft.FontWeight.BOLD),
            ft.Text(subtitle, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
        ],
        spacing=4,
    )
    return ft.Row(
        [title_block, action] if action else [title_block],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
    )


def empty_state(icon, title: str, message: str, action=None):
    controls = [
        ft.Icon(icon, size=38, color=ft.Colors.ON_SURFACE_VARIANT),
        ft.Text(title, size=18, weight=ft.FontWeight.W_600),
        ft.Text(message, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
    ]
    if action:
        controls.append(action)
    return ft.Container(
        content=ft.Column(controls, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        padding=32,
        expand=True,
        alignment=ft.Alignment.CENTER,
    )


def entity_list(app, title, description, items, editor, icon, empty_text, describe):
    add = ft.FilledButton("Hinzufügen", icon=ft.Icons.ADD, on_click=lambda _: editor(None))
    header = page_heading(title, description, add)
    if not items:
        content = empty_state(
            icon,
            f"Noch keine {title.lower()}",
            empty_text,
            ft.OutlinedButton("Ersten Eintrag erstellen", icon=ft.Icons.ADD, on_click=lambda _: editor(None)),
        )
    else:
        rows = []
        for item in sorted(items, key=lambda entry: entry.name.casefold()):
            rows.append(
                ft.Card(
                    variant=ft.CardVariant.FILLED,
                    elevation=0,
                    content=ft.ListTile(
                        leading=ft.Icon(icon, color=ft.Colors.PRIMARY),
                        title=ft.Text(item.name, weight=ft.FontWeight.W_600),
                        subtitle=ft.Text(describe(item), max_lines=2),
                        trailing=ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Bearbeiten", on_click=lambda _, value=item: editor(value)),
                        on_click=lambda _, value=item: editor(value),
                    ),
                )
            )
        content = ft.ListView(controls=rows, expand=True, spacing=8, padding=ft.Padding.only(top=8, bottom=12))
    return ft.Column([header, content], expand=True, spacing=20)
