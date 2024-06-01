import factory
import factory.fuzzy


class TeamHandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'teams.TeamHand'

    team = factory.SubFactory('ery_backend.teams.factories.TeamFactory')
    hand = factory.SubFactory('ery_backend.hands.factories.HandFactory')


class TeamNetworkDefinitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'teams.TeamNetworkDefinition'

    name = factory.Faker('name')
    comment = factory.fuzzy.FuzzyText(length=100)
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
    static_network = factory.fuzzy.FuzzyText(length=100)
    generation_method = factory.fuzzy.FuzzyChoice(['connected_newman_watts_strogatz_graph', 'neighborhood_graph'])


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'teams.Team'

    stint = factory.SubFactory('ery_backend.stints.factories.StintFactory')
    era = factory.SubFactory('ery_backend.syncs.factories.EraFactory')
    team_network_definition = factory.SubFactory(
        'ery_backend.teams.factories.TeamNetworkDefinitionFactory',
        static_network="Test static network",
        generation_method=None,
    )


class TeamNetworkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'teams.TeamNetwork'

    stint = factory.SubFactory('ery_backend.stints.factories.StintFactory')
    network = factory.fuzzy.FuzzyText(length=100)
