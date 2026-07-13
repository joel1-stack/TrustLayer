from django.db import migrations

OLD_TO_NEW = {
    'CREATED': 'CREATED',
    'PAYMENT_PENDING': 'SUBMITTED',
    'COLLECTED': 'AVAILABLE',
    'WAITING': 'HELD',
    'READY': 'READY',
    'SETTLING': 'SETTLING',
    'SETTLED': 'SETTLED',
    'REFUNDED': 'REFUNDED',
    'CANCELLED': 'CANCELLED',
}


def migrate_old_states(apps, schema_editor):
    Agreement = apps.get_model('agreements', 'Agreement')
    StateTransition = apps.get_model('state_machine', 'StateTransition')

    for old_state, new_state in OLD_TO_NEW.items():
        updated = Agreement.objects.filter(status=old_state).update(status=new_state)
        if updated:
            print(f"  Migrated {updated} agreements: {old_state} -> {new_state}")

    migrated = 0
    for transition in StateTransition.objects.all():
        old_from = OLD_TO_NEW.get(transition.from_status)
        old_to = OLD_TO_NEW.get(transition.to_status)
        if old_from:
            transition.from_status = old_from
        if old_to:
            transition.to_status = old_to
        if old_from or old_to:
            transition.save(update_fields=['from_status', 'to_status'])
            migrated += 1
    if migrated:
        print(f"  Migrated {migrated} state transitions")


def reverse_migration(apps, schema_editor):
    NEW_TO_OLD = {v: k for k, v in OLD_TO_NEW.items()}

    Agreement = apps.get_model('agreements', 'Agreement')
    StateTransition = apps.get_model('state_machine', 'StateTransition')

    for new_state, old_state in NEW_TO_OLD.items():
        updated = Agreement.objects.filter(status=new_state).update(status=old_state)
        if updated:
            print(f"  Reverted {updated} agreements: {new_state} -> {old_state}")

    migrated = 0
    for transition in StateTransition.objects.all():
        old_from = NEW_TO_OLD.get(transition.from_status)
        old_to = NEW_TO_OLD.get(transition.to_status)
        if old_from:
            transition.from_status = old_from
        if old_to:
            transition.to_status = old_to
        if old_from or old_to:
            transition.save(update_fields=['from_status', 'to_status'])
            migrated += 1
    if migrated:
        print(f"  Reverted {migrated} state transitions")


class Migration(migrations.Migration):

    dependencies = [
        ('agreements', '0003_alter_agreement_status'),
    ]

    operations = [
        migrations.RunPython(migrate_old_states, reverse_migration),
    ]
