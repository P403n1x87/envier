from typing import Callable
from typing import Optional
from typing import Type

from mypy.exprtotype import expr_to_unanalyzed_type
from mypy.nodes import AssignmentStmt
from mypy.nodes import CallExpr
from mypy.plugin import ClassDefContext
from mypy.plugin import MethodContext
from mypy.plugin import Plugin
from mypy.typeops import make_simplified_union
from mypy.types import Instance


_envier_attr_makers = frozenset(
    {"envier.env.Env.%s" % m for m in ("v", "d", "var", "der")}
)

_envier_base_classes = frozenset({"envier.En", "envier.Env"})


def _envier_attr_callback(ctx):
    # type: (MethodContext) -> Type
    arg_type = ctx.arg_types[0][0]
    if isinstance(arg_type, Instance):
        # WARNING: This returns an UnboundType which seems to match whatever!
        return expr_to_unanalyzed_type(ctx.args[0][0], ctx.api.options)

    return make_simplified_union({_.ret_type for _ in arg_type.items})


def _envier_base_class_callback(ctx):
    # type: (ClassDefContext) -> None
    for stmt in ctx.cls.defs.body:
        if isinstance(stmt, AssignmentStmt):
            decl = stmt.rvalue
            if (
                len(stmt.lvalues) != 1
                or not isinstance(decl, CallExpr)
                or not decl.callee.expr.fullname in _envier_base_classes
            ):
                # We assume a single assignment per line, so this can't be an
                # envier attribute maker.
                continue

            (attr,) = stmt.lvalues

            attr.node.type = ctx.api.anal_type(
                expr_to_unanalyzed_type(decl.args[0], ctx.api.options)
            )

            attr.is_inferred_def = False


class EnvierPlugin(Plugin):
    def get_method_hook(self, fullname):
        # type: (str) -> Optional[Callable[[MethodContext], Type]]
        if fullname in _envier_attr_makers:
            # We use this callback to override the the method return value to
            # match the attribute value, which is also inferred by the `type`
            # argument.
            return _envier_attr_callback

        return None

    def get_base_class_hook(self, fullname):
        # type: (str) -> Optional[Callable[[ClassDefContext], None]]
        if fullname in _envier_base_classes:
            # We use this callback to override the class attribute types to
            # match the ones declared by the `type` argument of the Env methods.
            return _envier_base_class_callback

        return None


def plugin(version):
    # type: (str) -> Plugin
    return EnvierPlugin
