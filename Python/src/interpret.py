import sys
from antlr4 import *
from stella.stellaParser import stellaParser
from stella.stellaLexer import stellaLexer


def compare_types(expected: str, actual: str):
    """
    helps to compare two types by removing parenthesis.
    return True if strings that represent types are identical, False otherwise.
    """

    if expected is None or actual is None:
        return False

    expected = expected.replace('(', '').replace(')', '')
    actual = actual.replace('(', '').replace(')', '')

    return expected == actual


class Handler:

    def __init__(self):
        self.variables = {'0': 'Nat', '1': 'Nat'}
        self.functions = {}

    def handle_expr_context(
            self,
            ctx: stellaParser.ExprContext,
    ):
        """
        handles expression context, checks type consistency of expression.
        passes: stellaParser.ExprContext instance.
        returns: actual type of expression.
        """

        if isinstance(ctx, stellaParser.ConstTrueContext):
            """
            returns Bool type if expression is 'true'
            """
            return 'Bool'

        elif isinstance(ctx, stellaParser.ConstFalseContext):
            """
            returns Bool type if expression is 'false'
            """
            return 'Bool'

        elif isinstance(ctx, stellaParser.SuccContext):
            """
            handles succ expression context
            returns Nat if argument is Nat
            raises RuntimeError otherwise
            """

            if self.handle_expr_context(ctx.n) == 'Nat':
                return 'Nat'
            else:
                raise RuntimeError(f'in "{ctx.getText()}": Nat expected, got {self.handle_expr_context(ctx.n)}')

        elif isinstance(ctx, stellaParser.IfContext):
            """
            handles if a then b else c expression context
            return type of b, if types of b and c are same and a is Bool
            raises RuntimeError otherwise 
            """

            condition_type = self.handle_expr_context(ctx.condition)
            then_type = self.handle_expr_context(ctx.thenExpr)
            else_type = self.handle_expr_context(ctx.elseExpr)

            if condition_type == 'Bool' and then_type == else_type:
                return then_type
            else:
                if condition_type != 'Bool':
                    raise RuntimeError(f'in condition expression "{ctx.condition.getText()}": Bool expected, got '
                                       f'{self.handle_expr_context(ctx.condition)}')
                else:
                    raise RuntimeError(f'then "{ctx.thenExpr.getText()}" and else "{ctx.elseExpr.getText()}" '
                                       f'expressions have different types, {then_type} and {else_type} respectively')

        elif isinstance(ctx, stellaParser.VarContext):
            """
            handles var context
            returns type of variable
            """

            if ctx.name.text in self.variables:
                return self.variables[ctx.name.text]
            else:
                return None

        elif isinstance(ctx, stellaParser.NatRecContext):
            """
            handles Nat::rec(n, z, s) context
            return type of z (initial value), if type of Nat::rec is fn(Nat) -> (fn(T) -> T),
                where T is type of z.
            raises RuntmeError otherwise 
            """

            t = self.variables[ctx.initial.getText()]
            expected_type = f'fn(Nat)->(fn({t})->({t}))'
            actual_type = self.handle_expr_context(ctx.step)

            if self.variables[ctx.n.getText()] == 'Nat' and compare_types(expected_type, actual_type):
                return t
            else:
                if self.variables[ctx.n.getText()] != 'Nat':
                    raise RuntimeError(f'in Nat::rec expression in input value {ctx.n.getText()}: Nat expected, '
                                       f'got {self.handle_expr_context(ctx.n)}')
                else:
                    raise RuntimeError(f'in Nat::rec expression in function: {expected_type} expected, '
                                       f'got {actual_type}')

        elif isinstance(ctx, stellaParser.AbstractionContext):
            """
            handles abstractions
            returns type of abstract function
            """

            local_params = {
                param.name.text: param.paramType.getText()
                for param in ctx.paramDecls
            }

            local_type = None

            for param in local_params:
                local_type = local_params[param]

            self.variables.update(local_params)
            return f'fn({local_type})->({self.handle_expr_context(ctx.returnExpr)})'

        elif isinstance(ctx, stellaParser.ApplicationContext):
            """
            handles application
            returns type of applied function
            """

            if isinstance(ctx.fun, stellaParser.VarContext):
                return self.functions[ctx.fun.getText().split('(')[0]]['return_type']
            else:
                return self.handle_expr_context(ctx.args[0])

        elif isinstance(ctx, stellaParser.ConstIntContext):
            """
            handles constant integers context
            returns 'Nat' string corresponding to Nat type
            """
            return 'Nat'

        else:
            print(type(ctx))
            raise RuntimeError("unsupported syntax")

    def handle_decl_context(self, ctx: stellaParser.DeclContext):
        """
        handles declaration context, checks type consistency of declaration and its return expression.
        passes: stellaParser.DeclContext instance.
        returns nothing if typecheck is successfully passed, raises corresponding log message otherwise.
        """

        if isinstance(ctx, stellaParser.DeclFunContext):

            local_params = {
                param.name.text: param.paramType.getText()
                for param in ctx.paramDecls
            }

            local_type = None

            for param in local_params:
                local_type = local_params[param]

            self.variables.update(local_params)
            expected_return_type = ctx.returnType.getText()

            self.functions.update({
                ctx.name.text: {
                    'param_type': local_type,
                    'return_type': expected_return_type,
                }
            })

            if isinstance(ctx.returnExpr, stellaParser.ExprContext):

                try:
                    return_type = self.handle_expr_context(ctx.returnExpr)

                    if isinstance(ctx.returnExpr, stellaParser.ApplicationContext):

                        declaration_name = ctx.name.text
                        application_name = ctx.returnExpr.getText().split('(')[0]

                        declaration_param_type = self.functions[declaration_name]['param_type']
                        application_param_type = self.functions[application_name]['param_type']

                        if not compare_types(declaration_param_type, application_param_type):
                            raise RuntimeError(f'declaration param type is {declaration_param_type}, while '
                                               f'application param type is {application_param_type}')

                        declaration_return_type = self.functions[declaration_name]['return_type']
                        application_return_type = self.handle_expr_context(ctx.returnExpr)

                        if not compare_types(declaration_return_type, application_return_type):
                            raise RuntimeError(f'declaration return type is {declaration_return_type}, while '
                                               f'application return type is {application_return_type}')

                    if isinstance(ctx.returnExpr, stellaParser.AbstractionContext):

                        declaration_name = ctx.name.text
                        declaration_return_type = self.functions[declaration_name]['return_type']

                        # print(ctx.returnExpr.paramDecls[0].paramType.getText())
                        # print(self.handle_expr_context(ctx.returnExpr))

                        if not compare_types(declaration_return_type, return_type):
                            raise RuntimeError(f'declaration return type is {declaration_return_type}, while '
                                               f'abstraction return type is {return_type}')

                    if not compare_types(expected_return_type, return_type):
                        raise RuntimeError(f'declaration return type is {expected_return_type}, while '
                                           f'return type is {return_type}')

                except RuntimeError as error:
                    print(f'[TYPE ERROR] "{ctx.name.text}": {error}')

        elif isinstance(ctx, stellaParser.DeclTypeAliasContext):
            raise RuntimeError("\t\tunsupported syntax")

        else:
            raise RuntimeError("\t\tunsupported syntax")

    def handle_program_context(self, ctx: stellaParser.ProgramContext):
        """
        handles program context.
        passes: stellaParser.ProgramContext instance.
        """

        for decl in ctx.decls:
            self.handle_decl_context(decl)


def main(argv):

    if len(argv) > 1:
        input_stream = FileStream(argv[1])
    else:
        input_stream = StdinStream()

    lexer = stellaLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = stellaParser(stream)

    program = parser.program()
    handler = Handler()
    handler.handle_program_context(program)


if __name__ == '__main__':
    main(sys.argv)
