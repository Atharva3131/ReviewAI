"""
SQL injection prevention and database security utilities
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

import sqlparse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlparse.sql import Function, Identifier, IdentifierList
from sqlparse.tokens import DML, Keyword

logger = logging.getLogger(__name__)


class SQLInjectionError(Exception):
    """Exception raised when SQL injection attempt is detected"""

    def __init__(self, message: str, query: str = None, parameters: Dict = None):
        self.message = message
        self.query = query
        self.parameters = parameters
        super().__init__(self.message)


class SQLSecurityValidator:
    """Validator for SQL security and injection prevention"""

    # Dangerous SQL keywords that should not appear in user input
    DANGEROUS_KEYWORDS = {
        "DROP",
        "DELETE",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "INSERT",
        "UPDATE",
        "EXEC",
        "EXECUTE",
        "UNION",
        "SCRIPT",
        "DECLARE",
        "CAST",
        "CONVERT",
        "INFORMATION_SCHEMA",
        "SYSOBJECTS",
        "SYSCOLUMNS",
        "SYSUSERS",
        "xp_cmdshell",
        "sp_executesql",
        "sp_configure",
        "sp_adduser",
        "OPENROWSET",
        "OPENDATASOURCE",
        "BULK",
        "LOAD_FILE",
        "INTO OUTFILE",
    }

    # SQL injection patterns
    INJECTION_PATTERNS = [
        # Comment patterns
        r"--[^\r\n]*",
        r"/\*.*?\*/",
        r"#[^\r\n]*",
        # Union-based injection
        r"\bUNION\s+(ALL\s+)?SELECT\b",
        # Boolean-based injection
        r"\b(AND|OR)\s+\d+\s*=\s*\d+",
        r'\b(AND|OR)\s+[\'"]?\w+[\'"]?\s*=\s*[\'"]?\w+[\'"]?',
        r"\b(AND|OR)\s+\d+\s*<>\s*\d+",
        # Time-based injection
        r"\bWAITFOR\s+DELAY\b",
        r"\bSLEEP\s*\(",
        r"\bBENCHMARK\s*\(",
        # Error-based injection
        r"\bCONVERT\s*\(",
        r"\bCAST\s*\(",
        r"\bEXTRACTVALUE\s*\(",
        # Stacked queries
        r";\s*(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|EXEC)",
        # Information gathering
        r"\bINFORMATION_SCHEMA\b",
        r"\bSYSOBJECTS\b",
        r"\bSYSCOLUMNS\b",
        # Function-based injection
        r"\bxp_\w+",
        r"\bsp_\w+",
        # Hex encoding attempts
        r"0x[0-9a-fA-F]+",
        # Char/ASCII function abuse
        r"\bCHAR\s*\(\s*\d+\s*\)",
        r"\bASCII\s*\(",
    ]

    @classmethod
    def validate_query_string(
        cls, query: str, allow_keywords: List[str] = None
    ) -> bool:
        """
        Validate a query string for potential SQL injection

        Args:
            query: SQL query string to validate
            allow_keywords: List of keywords to allow (overrides dangerous keywords)

        Returns:
            True if query is safe, False otherwise

        Raises:
            SQLInjectionError: If injection attempt is detected
        """
        if not isinstance(query, str):
            raise SQLInjectionError("Query must be a string")

        query_upper = query.upper()
        allow_keywords = allow_keywords or []

        # Check for dangerous keywords
        dangerous_found = []
        for keyword in cls.DANGEROUS_KEYWORDS:
            if keyword not in allow_keywords and keyword in query_upper:
                dangerous_found.append(keyword)

        if dangerous_found:
            raise SQLInjectionError(
                f"Dangerous SQL keywords detected: {', '.join(dangerous_found)}",
                query=query,
            )

        # Check for injection patterns
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE | re.MULTILINE):
                raise SQLInjectionError(
                    f"Potential SQL injection pattern detected: {pattern}", query=query
                )

        return True

    @classmethod
    def validate_user_input(cls, user_input: str, context: str = "general") -> str:
        """
        Validate and sanitize user input that might be used in SQL queries

        Args:
            user_input: User input to validate
            context: Context of the input (e.g., 'search', 'filter', 'sort')

        Returns:
            Sanitized input

        Raises:
            SQLInjectionError: If injection attempt is detected
        """
        if not isinstance(user_input, str):
            return str(user_input)

        # Check for SQL injection patterns in user input
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                logger.warning(
                    f"SQL injection attempt detected in {context}: {pattern}",
                    extra={"user_input": user_input[:100], "context": context},
                )
                raise SQLInjectionError(
                    f"Invalid input detected in {context}", query=user_input
                )

        # Context-specific validation
        if context == "sort":
            return cls._validate_sort_input(user_input)
        elif context == "filter":
            return cls._validate_filter_input(user_input)
        elif context == "search":
            return cls._validate_search_input(user_input)

        return user_input

    @classmethod
    def _validate_sort_input(cls, sort_input: str) -> str:
        """Validate sort column input"""
        # Only allow alphanumeric characters, underscores, and dots for table.column
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", sort_input):
            raise SQLInjectionError("Invalid sort column name")

        # Prevent excessively long column names
        if len(sort_input) > 64:
            raise SQLInjectionError("Sort column name too long")

        return sort_input

    @classmethod
    def _validate_filter_input(cls, filter_input: str) -> str:
        """Validate filter input"""
        # Basic sanitization for filter values
        # Remove potential SQL metacharacters
        sanitized = re.sub(r"[;\'\"\\]", "", filter_input)

        # Check length
        if len(sanitized) > 255:
            raise SQLInjectionError("Filter value too long")

        return sanitized

    @classmethod
    def _validate_search_input(cls, search_input: str) -> str:
        """Validate search input"""
        # Remove SQL metacharacters but allow more flexibility for search
        sanitized = re.sub(r"[;\'\"\\]", "", search_input)

        # Check length
        if len(sanitized) > 500:
            raise SQLInjectionError("Search query too long")

        return sanitized


class SafeQueryBuilder:
    """Builder for constructing safe SQL queries with parameterization"""

    def __init__(self, session: Session):
        self.session = session
        self.query_parts = []
        self.parameters = {}
        self.parameter_counter = 0

    def select(self, columns: Union[str, List[str]]) -> "SafeQueryBuilder":
        """Add SELECT clause"""
        if isinstance(columns, str):
            columns = [columns]

        # Validate column names
        for column in columns:
            SQLSecurityValidator.validate_user_input(column, context="sort")

        columns_str = ", ".join(columns)
        self.query_parts.append(f"SELECT {columns_str}")
        return self

    def from_table(self, table_name: str) -> "SafeQueryBuilder":
        """Add FROM clause"""
        # Validate table name
        SQLSecurityValidator.validate_user_input(table_name, context="sort")

        self.query_parts.append(f"FROM {table_name}")
        return self

    def where(self, condition: str, **params) -> "SafeQueryBuilder":
        """Add WHERE clause with parameters"""
        # Validate condition structure (should contain parameter placeholders)
        if not re.search(r":\w+", condition):
            logger.warning("WHERE condition without parameters detected")

        # Add parameters
        for key, value in params.items():
            param_key = f"param_{self.parameter_counter}_{key}"
            self.parameters[param_key] = value
            condition = condition.replace(f":{key}", f":{param_key}")
            self.parameter_counter += 1

        if self.query_parts and "WHERE" in self.query_parts[-1]:
            self.query_parts.append(f"AND {condition}")
        else:
            self.query_parts.append(f"WHERE {condition}")

        return self

    def order_by(self, column: str, direction: str = "ASC") -> "SafeQueryBuilder":
        """Add ORDER BY clause"""
        # Validate column name and direction
        SQLSecurityValidator.validate_user_input(column, context="sort")

        if direction.upper() not in ["ASC", "DESC"]:
            raise SQLInjectionError("Invalid sort direction")

        self.query_parts.append(f"ORDER BY {column} {direction.upper()}")
        return self

    def limit(self, count: int, offset: int = 0) -> "SafeQueryBuilder":
        """Add LIMIT clause"""
        if not isinstance(count, int) or count < 0:
            raise SQLInjectionError("Invalid limit count")

        if not isinstance(offset, int) or offset < 0:
            raise SQLInjectionError("Invalid offset")

        if offset > 0:
            self.query_parts.append(f"LIMIT {count} OFFSET {offset}")
        else:
            self.query_parts.append(f"LIMIT {count}")

        return self

    def build(self) -> str:
        """Build the final query string"""
        query = " ".join(self.query_parts)

        # Validate the complete query
        SQLSecurityValidator.validate_query_string(
            query, allow_keywords=["SELECT", "FROM", "WHERE", "ORDER", "LIMIT"]
        )

        return query

    def execute(self):
        """Execute the query safely"""
        query = self.build()

        try:
            result = self.session.execute(text(query), self.parameters)
            return result
        except SQLAlchemyError as e:
            logger.error(f"SQL execution error: {e}")
            raise SQLInjectionError(f"Query execution failed: {str(e)}")


class DatabaseSecurityAuditor:
    """Auditor for database security and query monitoring"""

    def __init__(self, session: Session):
        self.session = session

    def audit_query(self, query: str, parameters: Dict = None) -> Dict[str, Any]:
        """
        Audit a query for security issues

        Args:
            query: SQL query to audit
            parameters: Query parameters

        Returns:
            Audit result dictionary
        """
        audit_result = {
            "query": query,
            "parameters": parameters,
            "security_issues": [],
            "recommendations": [],
            "risk_level": "low",
        }

        try:
            # Parse the query
            parsed = sqlparse.parse(query)[0]

            # Check for dangerous operations
            self._check_dangerous_operations(parsed, audit_result)

            # Check for missing parameterization
            self._check_parameterization(query, parameters, audit_result)

            # Check for information disclosure risks
            self._check_information_disclosure(parsed, audit_result)

            # Determine overall risk level
            self._calculate_risk_level(audit_result)

        except Exception as e:
            audit_result["security_issues"].append(f"Query parsing error: {e}")
            audit_result["risk_level"] = "high"

        return audit_result

    def _check_dangerous_operations(self, parsed_query, audit_result):
        """Check for dangerous SQL operations"""
        query_str = str(parsed_query).upper()

        # Check for data modification without WHERE clause
        if (
            any(op in query_str for op in ["DELETE", "UPDATE"])
            and "WHERE" not in query_str
        ):
            audit_result["security_issues"].append(
                "Data modification without WHERE clause"
            )
            audit_result["recommendations"].append(
                "Always use WHERE clause with DELETE/UPDATE"
            )

        # Check for SELECT *
        if "SELECT *" in query_str:
            audit_result["security_issues"].append("SELECT * usage detected")
            audit_result["recommendations"].append(
                "Specify explicit column names instead of SELECT *"
            )

        # Check for administrative functions
        admin_functions = ["xp_", "sp_", "EXEC", "EXECUTE"]
        for func in admin_functions:
            if func in query_str:
                audit_result["security_issues"].append(
                    f"Administrative function detected: {func}"
                )
                audit_result["recommendations"].append(
                    "Avoid administrative functions in application queries"
                )

    def _check_parameterization(self, query: str, parameters: Dict, audit_result):
        """Check for proper parameterization"""
        # Look for string concatenation patterns
        concat_patterns = [
            r"'\s*\+\s*",  # ' +
            r"\+\s*'",  # + '
            r'"\s*\+\s*',  # " +
            r'\+\s*"',  # + "
        ]

        for pattern in concat_patterns:
            if re.search(pattern, query):
                audit_result["security_issues"].append(
                    "String concatenation detected in query"
                )
                audit_result["recommendations"].append(
                    "Use parameterized queries instead of string concatenation"
                )
                break

        # Check if parameters are used
        if ":" in query and not parameters:
            audit_result["security_issues"].append(
                "Query has parameter placeholders but no parameters provided"
            )

        # Check for literal values that should be parameterized
        literal_patterns = [
            r"=\s*'[^']*'",  # = 'value'
            r'=\s*"[^"]*"',  # = "value"
            r"=\s*\d+",  # = 123
        ]

        for pattern in literal_patterns:
            if re.search(pattern, query):
                audit_result["security_issues"].append(
                    "Literal values detected - consider parameterization"
                )
                audit_result["recommendations"].append(
                    "Use parameters for dynamic values"
                )
                break

    def _check_information_disclosure(self, parsed_query, audit_result):
        """Check for information disclosure risks"""
        query_str = str(parsed_query).upper()

        # Check for system table access
        system_tables = ["INFORMATION_SCHEMA", "SYS", "MYSQL", "PG_"]
        for table in system_tables:
            if table in query_str:
                audit_result["security_issues"].append(
                    f"System table access detected: {table}"
                )
                audit_result["recommendations"].append(
                    "Avoid querying system tables from application code"
                )

        # Check for error-prone functions
        error_functions = ["CONVERT", "CAST", "EXTRACTVALUE"]
        for func in error_functions:
            if func in query_str:
                audit_result["security_issues"].append(
                    f"Error-prone function detected: {func}"
                )
                audit_result["recommendations"].append(
                    "Handle conversion errors properly"
                )

    def _calculate_risk_level(self, audit_result):
        """Calculate overall risk level based on issues found"""
        issue_count = len(audit_result["security_issues"])

        # Check for high-risk patterns
        high_risk_keywords = [
            "administrative function",
            "system table",
            "without WHERE clause",
        ]
        has_high_risk = any(
            any(keyword in issue.lower() for keyword in high_risk_keywords)
            for issue in audit_result["security_issues"]
        )

        if has_high_risk:
            audit_result["risk_level"] = "high"
        elif issue_count >= 3:
            audit_result["risk_level"] = "medium"
        elif issue_count >= 1:
            audit_result["risk_level"] = "low"
        else:
            audit_result["risk_level"] = "minimal"


class SecureORMWrapper:
    """Wrapper for ORM operations with additional security checks"""

    def __init__(self, session: Session):
        self.session = session
        self.auditor = DatabaseSecurityAuditor(session)

    def safe_execute(self, query: str, parameters: Dict = None, audit: bool = True):
        """
        Execute query with security validation

        Args:
            query: SQL query to execute
            parameters: Query parameters
            audit: Whether to perform security audit

        Returns:
            Query result

        Raises:
            SQLInjectionError: If security issues are detected
        """
        # Validate query
        SQLSecurityValidator.validate_query_string(query)

        # Audit if requested
        if audit:
            audit_result = self.auditor.audit_query(query, parameters)

            if audit_result["risk_level"] in ["high", "critical"]:
                logger.error(f"High-risk query blocked: {audit_result}")
                raise SQLInjectionError(
                    "Query blocked due to security concerns",
                    query=query,
                    parameters=parameters,
                )

            if audit_result["security_issues"]:
                logger.warning(f"Query security issues: {audit_result}")

        # Execute query
        try:
            if parameters:
                result = self.session.execute(text(query), parameters)
            else:
                result = self.session.execute(text(query))

            return result

        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise SQLInjectionError(f"Query execution failed: {str(e)}")

    def safe_filter(self, model_class, filters: Dict[str, Any]):
        """
        Apply filters safely using ORM

        Args:
            model_class: SQLAlchemy model class
            filters: Dictionary of column: value filters

        Returns:
            Filtered query object
        """
        query = self.session.query(model_class)

        # Get model columns for validation
        mapper = inspect(model_class)
        valid_columns = {col.key for col in mapper.columns}

        for column, value in filters.items():
            # Validate column name
            if column not in valid_columns:
                raise SQLInjectionError(f"Invalid column name: {column}")

            # Validate value
            if isinstance(value, str):
                SQLSecurityValidator.validate_user_input(value, context="filter")

            # Apply filter using ORM (safe from injection)
            query = query.filter(getattr(model_class, column) == value)

        return query
