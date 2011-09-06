import gtk
import odml
from ... import format
import commands
from TreeView import TreeView
from odml.tools.treemodel import SectionModel

COL_KEY = 0
COL_VALUE = 1
class ValueView(TreeView):
    """
    The Main treeview for editing properties and their value-attributes
    """
    def __init__(self, execute_func=lambda x: x()):
        self.execute = execute_func

        super(ValueView, self).__init__()
        tv = self._treeview

        for name, (id, propname) in SectionModel.ColMapper.sort_iteritems():
            column = self.add_column(
                name=name,
                edit_func=self.on_edited,
                id=id, data=propname)
            if name == "Value":
                tv.set_expander_column(column)

        tv.set_headers_visible(True)
        tv.set_rules_hint(True)
        tv.show()

    @property
    def section(self):
        return self._section

    @section.setter
    def section(self, section):
        self._section = section
        if self.model:
            self.model.destroy()
        self.model = SectionModel.SectionModel(section)

    @property
    def model(self):
        return self._treeview.get_model()

    @model.setter
    def model(self, new_value):
        self._treeview.set_model(new_value)

    def on_selection_change(self, tree_selection):
        (model, tree_iter) = tree_selection.get_selected()
        if not tree_iter:
            return

        obj = model.get_object(tree_iter)
        print "select", obj
        self.on_property_select(obj)

    def on_property_select(self, prop):
        """called when a different property is selected"""
        pass

    def on_object_edit(self, tree_iter, column_name, new_text):
        """
        called upon an edit event of the list view

        updates the underlying model property that corresponds to the edited cell
        """
        section = self.section
        prop = tree_iter._obj

        # are we editing the first_row of a <multi> value?
        first_row = not tree_iter.parent
        first_row_of_multi = first_row and tree_iter.has_child

        # can only edit the subvalues, but not <multi> itself
        if first_row_of_multi and column_name == "value":
            return
        if not first_row and column_name == "name":
            return

        cmd = None
        # if we edit another attribute (e.g. unit), set this for all values of this property

        if first_row_of_multi and column_name != "name":
            # editing multiple values of a property at once
            cmds = []
            for value in prop.values:
                cmds.append(commands.ChangeValue(
                    object    = value,
                    attr      = [column_name, "value"],
                    new_value = new_text))

            cmd = commands.Multiple(cmds=cmds)

        else:

            # first row edit event for the value, so switch the object
            if column_name != "name" and first_row:
                prop = prop.values[0]
            if not (column_name == "name" and first_row):
                column_name = [column_name, "value"] # backup the value attribute too
            cmd = commands.ChangeValue(
                    object    = prop,
                    attr      = column_name,
                    new_value = new_text)

        if cmd:
            self.execute(cmd)

    def add_value(self, action):
        """
        popup menu action: add value

        add a value to the selected property
        """
        model, path, obj = self.popup_data

        # TODO this can be reached also if no property is selected
        #      the context-menu item should be disabled in this case?
        if obj is None:
            return

        val = odml.Value("")

        cmd = commands.AppendValue(obj=obj, val=val, model=self.model, path=path)

        def cmd_action(undo=False):
            model = self.model
            if model.section != cmd.model.section:
                return

            if not undo:
                # notify the current property row, that it might have got a new child
                model.row_has_child_toggled(cmd.path, model.get_iter(cmd.path))

                # notify the model about the newly inserted row
                path = model.odml_path_to_model_path(val.to_path(model.section))
                print val.to_path(model.section), path
                model.row_inserted(path, model.get_iter(path))
                cmd.val_path = path
            else:
                model.row_has_child_toggled(cmd.path, model.get_iter(cmd.path))
                model.row_deleted(cmd.val_path)

        cmd.on_action = cmd_action
        self.execute(cmd)


    def add_property(self, action):
        """
        popup menu action: add property

        add a property to the active section
        """
        model, path, obj = self.popup_data
        prop = odml.Property(name="unnamed property", value="")
        cmd = commands.AppendValue(
                obj = model.section,
                val = prop,
                model = self.model)

        def cmd_action(undo=False):
            # notify the model about the newly inserted row (unless the model changed anyways)
            model = self.model
            if model.section != cmd.model.section: return

            if undo:
                model.row_deleted(cmd.path)
            else:
                cmd.path = model.odml_path_to_model_path(prop.to_path(model.section))
                model.row_inserted(cmd.path, model.get_iter(cmd.path))

        cmd.on_action = cmd_action
        self.execute(cmd)