import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.testcases import GQLTestCase
from ery_backend.mutations import VendorMutation
from ery_backend.roles.utils import grant_role
from ery_backend.users.schema import ViewerQuery

from ..factories import VendorFactory
from ..models import Vendor


class TestQuery(ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(VendorMutation, graphene.ObjectType):
    pass


class TestReadVendor(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery))

    def test_read_all_requires_login(self):
        """allVendors query without a user is unauthorized"""
        query = """{viewer{ allVendors{ edges{ node{ id }}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_node_requires_login(self):
        vendor = VendorFactory()
        td = {"vendorid": vendor.gql_id}

        query = """query VendorQuery($vendorid: ID!){viewer{ vendor(id: $vendorid){ id }}}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

    def test_read_all_filters_by_privilege(self):
        query = """
{
    viewer{
        allVendors{
            edges{
                node{
                    id backgroundColor shortName icon{ id } homepageUrl themeColor
                }
            }
        }
    }
}"""
        vendors = [VendorFactory() for _ in range(3)]

        for obj in vendors:
            grant_role(self.viewer["role"], obj.get_privilege_ancestor(), self.viewer["user"])

        for obj in vendors[1:]:
            grant_role(self.editor["role"], obj.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], vendors[2].get_privilege_ancestor(), self.owner["user"])
        # No roles
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.no_roles["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allVendors"]["edges"]), 0)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allVendors"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allVendors"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["viewer"]["allVendors"]["edges"]), 1)


class TestCreateVendor(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.icon = ImageAssetFactory()
        self.td = {
            "backgroundColor": "#c2b84c",
            "shortName": "crocs",
            "icon": self.icon.gql_id,
            "homepageUrl": "dontwearcrocs.ery.sh",
            "themeColor": "#242329",
            "name": "dontwearcrocs",
            "comment": "Unless you\'re rich?",
        }

        self.query = """
mutation CreateVendor(
    $name: String!,
    $backgroundColor: String,
    $shortName: String,
    $icon: ID,
    $homepageUrl: String
    $themeColor: String,
    $comment: String
    ){
    createVendor(input: {
        name: $name,
        backgroundColor: $backgroundColor,
        shortName: $shortName,
        icon: $icon,
        homepageUrl: $homepageUrl,
        themeColor: $themeColor,
        comment: $comment
    }){
        vendorEdge {
            node {
                id
                name
                backgroundColor
                shortName
                icon {id}
                homepageUrl
                themeColor
                comment
            }
        }
    }
}
"""

    def test_create_requires_login(self):
        result = self.gql_client.execute(self.query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_create_produces_vendor(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)
        self.td.pop('icon')
        self.assertEqual(self.icon.gql_id, result["data"]["createVendor"]["vendorEdge"]["node"]["icon"]["id"])
        for field in self.td:
            result_value = result["data"]["createVendor"]["vendorEdge"]["node"][field]
            td_value = self.td[field]
            if isinstance(result_value, str):  # Due to returned values from enum fields
                result_value = result_value.lower()
                td_value = td_value.lower()
            self.assertEqual(result_value, td_value, msg=f"mismatch on {field}")

        lookup = Vendor.objects.get(id=from_global_id(result["data"]["createVendor"]["vendorEdge"]["node"]["id"])[1])

        self.assertEqual(lookup.icon, self.icon)


class TestUpdateVendor(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.vendor = VendorFactory()
        self.icon = ImageAssetFactory()
        self.td = {
            "vendorid": self.vendor.gql_id,
            "backgroundColor": "#c2b84c",
            "shortName": "crocs",
            "icon": self.icon.gql_id,
            "homepageUrl": "dontwearcrocs.ery.sh",
            "themeColor": "#242329",
            "name": "dontwearcrocs",
            "comment": "Unless you\'re rich?",
        }

        self.query = """
mutation UpdateVendor(
    $vendorid: ID!,
    $name: String!,
    $backgroundColor: String,
    $shortName: String,
    $icon: ID,
    $homepageUrl: String
    $themeColor: String,
    $comment: String
    ){
    updateVendor(input: {
        id: $vendorid
        name: $name,
        backgroundColor: $backgroundColor,
        shortName: $shortName,
        icon: $icon,
        homepageUrl: $homepageUrl,
        themeColor: $themeColor,
        comment: $comment
    }){
        vendor {
            id
            name
            backgroundColor
            shortName
            icon {id}
            homepageUrl
            themeColor
            comment
        }
    }
}
"""

    def test_update_requires_privilege(self):
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_vendor(self):
        grant_role(self.owner["role"], self.vendor.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)
        vendor_id = self.td.pop('vendorid')
        self.assertEqual(vendor_id, self.vendor.gql_id)

        self.assertEqual(result['data']['updateVendor']['vendor']['icon']['id'], self.icon.gql_id)
        self.td.pop('icon')

        for field in self.td:
            self.assertEqual(result["data"]["updateVendor"]["vendor"][field], self.td[field], msg=f"mismatch on {field}")


class TestDeleteVendor(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.vendor = VendorFactory()
        self.td = {"gqlId": self.vendor.gql_id}
        self.query = """mutation DeleteVendor($gqlId: ID!){ deleteVendor(input: {id: $gqlId}){id}}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.vendor.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        Vendor.objects.get(pk=self.vendor.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.vendor.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteVendor"]["id"])
        self.assertRaises(Vendor.DoesNotExist, Vendor.objects.get, **{"pk": self.vendor.id})
